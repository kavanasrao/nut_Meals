"""
Pydantic schemas for Stock Reservation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.stock_reservation import (
    ReferenceType,
    ReservationStatus,
)


class StockReservationCreate(BaseModel):
    warehouse_id: UUID
    product_id: str
    lot_id: UUID | None = None
    quantity: Decimal
    reference_type: ReferenceType
    reference_id: str
    expires_at: datetime | None = None


class StockReservationOut(BaseModel):
    id: UUID
    warehouse_id: UUID
    product_id: str
    lot_id: UUID | None

    quantity: Decimal

    status: ReservationStatus

    reference_type: ReferenceType
    reference_id: str

    reserved_at: datetime
    expires_at: datetime | None
    released_at: datetime | None

    created_at: datetime

    model_config = {
        "from_attributes": True,
    }