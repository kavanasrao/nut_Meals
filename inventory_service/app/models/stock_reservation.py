"""
Stock Reservation ORM model.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReservationStatus(str, enum.Enum):
    ACTIVE = "active"
    RELEASED = "released"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ReferenceType(str, enum.Enum):
    SALES_ORDER = "sales_order"
    PRODUCTION_BATCH = "production_batch"
    TRANSFER = "transfer"


class StockReservation(Base):
    __tablename__ = "stock_reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
        index=True,
    )

    product_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_lots.id"),
        nullable=True,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
    )

    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(
            ReservationStatus,
            name="reservation_status_enum",
        ),
        default=ReservationStatus.ACTIVE,
        nullable=False,
    )

    reference_type: Mapped[ReferenceType] = mapped_column(
        SAEnum(
            ReferenceType,
            name="reservation_reference_enum",
        ),
        nullable=False,
    )

    reference_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )