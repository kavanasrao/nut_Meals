"""Business logic for inventory reservations used by the Orders service.

Flow:
1. Orders service calls POST /reservations at checkout -> stock is held
   (quantity_reserved increases, available decreases) and a Celery task is
   scheduled to auto-release it at expiry.
2. On payment success, Orders calls POST /reservations/{id}/confirm ->
   quantity_on_hand and quantity_reserved both decrease (stock permanently
   consumed).
3. On payment failure/cancellation/timeout, the reservation is released ->
   quantity_reserved decreases, stock becomes available again.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.audit import record_movement
from app.models.reservation import ReservationStatus, StockReservation
from app.models.warehouse import MovementType, StockLevel
from app.schemas.reservation import ReservationCreate

settings = get_settings()


async def create_reservation(db: AsyncSession, payload: ReservationCreate, actor: str) -> StockReservation:
    stock = await db.scalar(
        select(StockLevel).where(
            StockLevel.warehouse_id == payload.warehouse_id,
            StockLevel.item_id == payload.item_id,
        ).with_for_update()
    )
    available = stock.quantity_available if stock else 0.0
    if not stock or available < payload.quantity:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Insufficient available stock: available={available}, requested={payload.quantity}",
        )

    stock.quantity_reserved = float(stock.quantity_reserved) + payload.quantity
    ttl = payload.ttl_seconds or settings.RESERVATION_TTL_SECONDS
    reservation = StockReservation(
        order_id=payload.order_id,
        item_id=payload.item_id,
        warehouse_id=payload.warehouse_id,
        quantity=payload.quantity,
        status=ReservationStatus.ACTIVE,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
    )
    db.add(reservation)

    await record_movement(
        db, item_id=payload.item_id, warehouse_id=payload.warehouse_id,
        movement_type=MovementType.RESERVATION_HOLD, quantity_delta=0,
        actor=actor, reference_id=payload.order_id,
        notes=f"Reserved {payload.quantity} units for order {payload.order_id}",
    )
    await db.commit()
    await db.refresh(reservation)
    return reservation


async def get_reservation(db: AsyncSession, reservation_id: uuid.UUID) -> StockReservation:
    reservation = await db.get(StockReservation, reservation_id)
    if not reservation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reservation not found")
    return reservation


async def confirm_reservation(db: AsyncSession, reservation_id: uuid.UUID, actor: str) -> StockReservation:
    reservation = await get_reservation(db, reservation_id)
    if reservation.status != ReservationStatus.ACTIVE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Reservation is {reservation.status.value}, not active")

    stock = await db.scalar(
        select(StockLevel).where(
            StockLevel.warehouse_id == reservation.warehouse_id,
            StockLevel.item_id == reservation.item_id,
        ).with_for_update()
    )
    stock.quantity_on_hand = float(stock.quantity_on_hand) - float(reservation.quantity)
    stock.quantity_reserved = float(stock.quantity_reserved) - float(reservation.quantity)

    reservation.status = ReservationStatus.CONFIRMED
    reservation.confirmed_at = datetime.now(timezone.utc)

    await record_movement(
        db, item_id=reservation.item_id, warehouse_id=reservation.warehouse_id,
        movement_type=MovementType.OUTBOUND, quantity_delta=-float(reservation.quantity),
        actor=actor, reference_id=reservation.order_id,
        notes=f"Order {reservation.order_id} payment confirmed; stock consumed",
    )
    await db.commit()
    await db.refresh(reservation)
    return reservation


async def release_reservation(
    db: AsyncSession, reservation_id: uuid.UUID, actor: str, reason: str = "manual_release"
) -> StockReservation:
    reservation = await get_reservation(db, reservation_id)
    if reservation.status != ReservationStatus.ACTIVE:
        return reservation  # idempotent no-op

    stock = await db.scalar(
        select(StockLevel).where(
            StockLevel.warehouse_id == reservation.warehouse_id,
            StockLevel.item_id == reservation.item_id,
        ).with_for_update()
    )
    if stock:
        stock.quantity_reserved = max(0.0, float(stock.quantity_reserved) - float(reservation.quantity))

    reservation.status = ReservationStatus.RELEASED
    reservation.released_at = datetime.now(timezone.utc)

    await record_movement(
        db, item_id=reservation.item_id, warehouse_id=reservation.warehouse_id,
        movement_type=MovementType.RESERVATION_RELEASE, quantity_delta=0,
        actor=actor, reference_id=reservation.order_id, notes=f"Released: {reason}",
    )
    await db.commit()
    await db.refresh(reservation)
    return reservation


async def release_expired_reservations(db: AsyncSession, actor: str = "system:celery") -> int:
    """Called periodically by a Celery beat task. Releases every ACTIVE
    reservation whose expiry has passed. Returns count released."""
    now = datetime.now(timezone.utc)
    stmt = select(StockReservation).where(
        StockReservation.status == ReservationStatus.ACTIVE,
        StockReservation.expires_at <= now,
    )
    expired = (await db.scalars(stmt)).all()
    for reservation in expired:
        await release_reservation(db, reservation.id, actor=actor, reason="ttl_expired")
    return len(expired)
