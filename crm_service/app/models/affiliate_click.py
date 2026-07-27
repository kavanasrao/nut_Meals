"""
Affiliate Click model.

Tracks every click on an affiliate referral link.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DeviceType(str, enum.Enum):
    DESKTOP = "DESKTOP"
    MOBILE = "MOBILE"
    TABLET = "TABLET"
    OTHER = "OTHER"


class AffiliateClick(Base):
    __tablename__ = "affiliate_clicks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    affiliate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "affiliates.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    referral_code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
    )

    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType),
        default=DeviceType.OTHER,
        nullable=False,
    )

    browser: Mapped[str | None] = mapped_column(
        String(100),
    )

    operating_system: Mapped[str | None] = mapped_column(
        String(100),
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
    )

    landing_page: Mapped[str | None] = mapped_column(
        String(500),
    )

    referrer_url: Mapped[str | None] = mapped_column(
        String(500),
    )

    session_id: Mapped[str | None] = mapped_column(
        String(120),
    )

    converted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    converted_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    affiliate = relationship(
        "Affiliate",
        back_populates="clicks",
        lazy="joined",
    )

    __table_args__ = (
        Index("ix_affiliate_click_date", "clicked_at"),
        Index("ix_affiliate_click_country", "country"),
        Index("ix_affiliate_click_device", "device_type"),
        Index("ix_affiliate_click_converted", "converted"),
    )

    def __repr__(self) -> str:
        return (
            f"<AffiliateClick("
            f"affiliate={self.affiliate_id}, "
            f"converted={self.converted})>"
        )