"""
Reverse logistics service: books reverse pickups against the original
carrier, links them to the original shipment, and coordinates with Orders
and Inventory once the return is received back at origin.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import CarrierAPIError
from app.adapters.registry import get_adapter
from app.models.carrier import Carrier
from app.models.shipment import Shipment, ShipmentStatus, ShipmentType
from app.services.audit import record_audit_event
from app.services.order_client import notify_inventory_of_return


class ReversePickupError(Exception):
    """Raised when a reverse pickup cannot be booked with the original carrier."""


async def create_reverse_pickup(
    db: AsyncSession,
    original_shipment: Shipment,
    reason: str,
    pickup_pincode: str,
    weight_kg: float,
    actor: str,
) -> Shipment:
    if not original_shipment.carrier_awb:
        raise ReversePickupError("Original shipment has no carrier AWB to reverse against")

    carrier = (await db.execute(select(Carrier).where(Carrier.id == original_shipment.carrier_id))).scalar_one()
    adapter = get_adapter(carrier.code)

    try:
        booking = await adapter.create_reverse_pickup(
            awb=original_shipment.carrier_awb,
            pickup_pincode=pickup_pincode,
            reason=reason,
            weight_kg=weight_kg,
        )
    except CarrierAPIError as exc:
        raise ReversePickupError(f"Reverse pickup booking failed: {exc}") from exc

    reverse_shipment = Shipment(
        id=uuid.uuid4(),
        order_id=original_shipment.order_id,
        carrier_id=carrier.id,
        carrier_awb=booking.carrier_awb,
        shipment_type=ShipmentType.REVERSE,
        status=ShipmentStatus.CREATED,
        origin_pincode=pickup_pincode,
        destination_pincode=original_shipment.origin_pincode,
        weight_kg=weight_kg,
        cod_amount=0,
        meta={"reason": reason, "original_shipment_id": str(original_shipment.id), "booking_response": booking.raw_response},
    )
    db.add(reverse_shipment)
    await db.flush()

    await record_audit_event(
        db,
        entity_type="shipment",
        entity_id=str(reverse_shipment.id),
        action="reverse_pickup_created",
        actor=actor,
        details={"original_shipment_id": str(original_shipment.id), "reason": reason},
    )
    return reverse_shipment


async def complete_return_and_restock(
    db: AsyncSession, reverse_shipment: Shipment, sku_items: list[dict], actor: str
) -> bool:
    """
    Called once a reverse shipment reaches DELIVERED (i.e. back at the
    warehouse). Notifies Inventory to restock and records the audit trail.
    """
    if reverse_shipment.shipment_type != ShipmentType.REVERSE:
        raise ReversePickupError("Shipment is not a reverse/return shipment")

    success = await notify_inventory_of_return(str(reverse_shipment.order_id), sku_items)
    await record_audit_event(
        db,
        entity_type="shipment",
        entity_id=str(reverse_shipment.id),
        action="return_restocked" if success else "return_restock_failed",
        actor=actor,
        details={"sku_items": sku_items},
    )
    return success
