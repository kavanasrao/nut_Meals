"""Delivery Assignment ORM model."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SAEnum, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DeliveryStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    PICKED_UP = "picked_up"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    delivery_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rider_id: Mapped[str | None] = mapped_column(String(255))
    rider_name: Mapped[str | None] = mapped_column(String(255))
    rider_phone: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[DeliveryStatus] = mapped_column(
        SAEnum(DeliveryStatus, name="delivery_status_enum", create_type=True),
        nullable=False,
        default=DeliveryStatus.ASSIGNED,
        index=True,
    )
    eta_minutes: Mapped[int | None] = mapped_column(Integer)
    delivery_address: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    user_lat: Mapped[float | None] = mapped_column(Float)
    user_lon: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
