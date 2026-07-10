"""
SQLAlchemy ORM model for customer return requests.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

if TYPE_CHECKING:
    from app.models.return_item import ReturnItem


class ReturnStatus(str, enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    PICKUP_SCHEDULED = "pickup_scheduled"
    INSPECTION_PENDING = "inspection_pending"
    COMPLETED = "completed"


class ReturnResolution(str, enum.Enum):
    REFUND = "refund"
    REPLACEMENT = "replacement"
    REJECT = "reject"


class ReturnTier(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    tier: Mapped[ReturnTier] = mapped_column(
        SAEnum(ReturnTier, name="return_tier_enum"),
        nullable=False,
    )

    resolution: Mapped[ReturnResolution | None] = mapped_column(
        SAEnum(ReturnResolution, name="return_resolution_enum"),
        nullable=True,
    )

    status: Mapped[ReturnStatus] = mapped_column(
        SAEnum(ReturnStatus, name="return_status_enum"),
        nullable=False,
        default=ReturnStatus.REQUESTED,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    items: Mapped[list["ReturnItem"]] = relationship(
        "ReturnItem",
        back_populates="return_request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )