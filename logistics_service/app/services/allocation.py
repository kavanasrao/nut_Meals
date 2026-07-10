"""
Allocation service: picks the best carrier for a shipment (via the rules
engine) and books it, automatically falling back to the next-best carrier
if the primary one's booking call fails.
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import CarrierAPIError
from app.adapters.registry import get_adapter
from app.models.carrier import Carrier, CarrierCode
from app.models.shipment import Shipment, ShipmentStatus, ShipmentType
from app.services.audit import record_audit_event
from app.services.serviceability import get_carrier_priority_order

logger = logging.getLogger(__name__)


class NoServiceableCarrierError(Exception):
    """Raised when no carrier can service the requested route."""


async def allocate_and_book_shipment(
    db: AsyncSession,
    order_id: uuid.UUID,
    origin_pincode: str,
    destination_pincode: str,
    weight_kg: float,
    cod_amount: float,
    actor: str,
    preferred_carrier: CarrierCode | None = None,
) -> Shipment:
    """
    Select a carrier (respecting an optional explicit preference) and attempt
    booking. On failure, fall through to the next-ranked carrier and log a
    `carrier_fallback` audit event, until one succeeds or all are exhausted.
    """
    priority_order = await get_carrier_priority_order(db, origin_pincode, destination_pincode, weight_kg)
    if not priority_order:
        raise NoServiceableCarrierError(
            f"No carrier services route {origin_pincode} -> {destination_pincode}"
        )

    if preferred_carrier and preferred_carrier in priority_order:
        priority_order.remove(preferred_carrier)
        priority_order.insert(0, preferred_carrier)

    last_error: Exception | None = None
    for attempt_index, carrier_code in enumerate(priority_order):
        adapter = get_adapter(carrier_code)
        try:
            booking = await adapter.create_shipment(
                order_id=str(order_id),
                origin_pincode=origin_pincode,
                destination_pincode=destination_pincode,
                weight_kg=weight_kg,
                cod_amount=cod_amount,
            )
        except CarrierAPIError as exc:
            last_error = exc
            logger.warning("Booking failed with %s (attempt %d): %s", carrier_code, attempt_index, exc)
            if attempt_index > 0:
                await record_audit_event(
                    db,
                    entity_type="shipment",
                    entity_id=str(order_id),
                    action="carrier_fallback",
                    actor=actor,
                    details={"failed_carrier": carrier_code.value, "error": str(exc)},
                )
            continue

        carrier_row = (
            await db.execute(select(Carrier).where(Carrier.code == carrier_code))
        ).scalar_one()

        shipment = Shipment(
            id=uuid.uuid4(),
            order_id=order_id,
            carrier_id=carrier_row.id,
            carrier_awb=booking.carrier_awb,
            shipment_type=ShipmentType.FORWARD,
            status=ShipmentStatus.CREATED,
            origin_pincode=origin_pincode,
            destination_pincode=destination_pincode,
            weight_kg=weight_kg,
            cod_amount=cod_amount,
            meta={"booking_response": booking.raw_response, "label_url": booking.label_url},
        )
        db.add(shipment)
        await db.flush()

        await record_audit_event(
            db,
            entity_type="shipment",
            entity_id=str(shipment.id),
            action="shipment_booked",
            actor=actor,
            details={"carrier": carrier_code.value, "awb": booking.carrier_awb, "fallback_attempts": attempt_index},
        )
        return shipment

    raise NoServiceableCarrierError(
        f"All carriers failed to book shipment for order {order_id}: {last_error}"
    )
