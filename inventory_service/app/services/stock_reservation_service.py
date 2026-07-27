"""
Business logic for Stock Reservation Management.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_reservation import (
    ReservationStatus,
    StockReservation,
)
from app.schemas.stock_reservation import (
    StockReservationCreate,
)


class StockReservationService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # ==========================================================
    # CREATE RESERVATION
    # ==========================================================

    async def reserve_stock(
        self,
        data: StockReservationCreate,
    ) -> StockReservation:

        reservation = StockReservation(
            warehouse_id=data.warehouse_id,
            product_id=data.product_id,
            lot_id=data.lot_id,
            quantity=data.quantity,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            expires_at=data.expires_at,
            status=ReservationStatus.ACTIVE,
        )

        self.db.add(reservation)

        await self.db.commit()
        await self.db.refresh(reservation)

        return reservation

    # ==========================================================
    # GET
    # ==========================================================

    async def get(
        self,
        reservation_id: UUID,
    ) -> StockReservation | None:

        result = await self.db.execute(
            select(StockReservation).where(
                StockReservation.id == reservation_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # LIST
    # ==========================================================

    async def list(self):

        result = await self.db.execute(
            select(StockReservation).order_by(
                StockReservation.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # ==========================================================
    # RELEASE
    # ==========================================================

    async def release_reservation(
        self,
        reservation: StockReservation,
    ) -> StockReservation:

        if reservation.status != ReservationStatus.ACTIVE:
            raise ValueError(
                "Only active reservations can be released."
            )

        reservation.status = ReservationStatus.RELEASED
        reservation.released_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(reservation)

        return reservation

    # ==========================================================
    # FULFILL
    # ==========================================================

    async def fulfill_reservation(
        self,
        reservation: StockReservation,
    ) -> StockReservation:

        if reservation.status != ReservationStatus.ACTIVE:
            raise ValueError(
                "Only active reservations can be fulfilled."
            )

        reservation.status = ReservationStatus.FULFILLED
        reservation.released_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(reservation)

        return reservation

    # ==========================================================
    # CANCEL
    # ==========================================================

    async def cancel_reservation(
        self,
        reservation: StockReservation,
    ) -> StockReservation:

        if reservation.status != ReservationStatus.ACTIVE:
            raise ValueError(
                "Only active reservations can be cancelled."
            )

        reservation.status = ReservationStatus.CANCELLED
        reservation.released_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(reservation)

        return reservation