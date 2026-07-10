"""
Tracking service: pulls tracking updates from the carrier adapter, persists
new events, updates shipment status, syncs with Orders, and triggers customer
notifications on meaningful status changes.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import CarrierAPIError
from app.adapters.registry import get_adapter
from app.models.carrier import Carrier
from app.models.shipment import Shipment, ShipmentStatus, TrackingEvent
from app.services.audit import record_audit_event
from app.services.notification import notify_shipment_status_change
from app.services.order_client import sync_order_shipment_status

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {ShipmentStatus.DELIVERED, ShipmentStatus.RTO, ShipmentStatus.CANCELLED, ShipmentStatus.FAILED}


async def sync_shipment_tracking(db: AsyncSession, shipment: Shipment, actor: str = "system") -> Shipment:
    """
    Fetch the latest tracking checkpoints for a single shipment, persist any
    new events (idempotent on event_time + status), and propagate status
    changes downstream.
    """
    if shipment.status in _TERMINAL_STATUSES or not shipment.carrier_awb:
        return shipment

    carrier = (await db.execute(select(Carrier).where(Carrier.id == shipment.carrier_id))).scalar_one()
    adapter = get_adapter(carrier.code)

    try:
        updates = await adapter.fetch_tracking(shipment.carrier_awb)
    except CarrierAPIError as exc:
        logger.warning("Tracking fetch failed for shipment %s: %s", shipment.id, exc)
        return shipment

    existing_times = {e.event_time for e in shipment.tracking_events}
    new_events = [u for u in updates if u.event_time not in existing_times]
    if not new_events:
        return shipment

    for update in sorted(new_events, key=lambda u: u.event_time):
        event = TrackingEvent(
            id=uuid.uuid4(),
            shipment_id=shipment.id,
            status=ShipmentStatus(update.status),
            location=update.location,
            remarks=update.remarks,
            event_time=update.event_time,
            raw_payload=update.raw_payload,
        )
        db.add(event)

    latest_status = ShipmentStatus(new_events[-1].status)
    status_changed = latest_status != shipment.status
    shipment.status = latest_status
    await db.flush()

    if status_changed:
        await record_audit_event(
            db,
            entity_type="shipment",
            entity_id=str(shipment.id),
            action="status_updated",
            actor=actor,
            details={"new_status": latest_status.value},
        )
        await sync_order_shipment_status(str(shipment.order_id), latest_status.value, shipment.carrier_awb)
        await notify_shipment_status_change(str(shipment.order_id), latest_status.value, shipment.carrier_awb)

    return shipment


async def get_shipments_needing_sync(db: AsyncSession) -> list[Shipment]:
    """Return all non-terminal shipments, for the periodic Celery sync task."""
    result = await db.execute(
        select(Shipment).where(Shipment.status.not_in(_TERMINAL_STATUSES), Shipment.carrier_awb.is_not(None))
    )
    return list(result.scalars().all())
