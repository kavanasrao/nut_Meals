"""
Affiliate model.

Represents an affiliate partner who can refer customers,
earn commissions, and receive payouts.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AffiliateStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


class CommissionType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class Affiliate(Base):
    __tablename__ = "affiliates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
    )

    affiliate_code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        unique=True,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
    )

    status: Mapped[AffiliateStatus] = mapped_column(
        Enum(AffiliateStatus),
        default=AffiliateStatus.PENDING,
        nullable=False,
    )

    commission_type: Mapped[CommissionType] = mapped_column(
        Enum(CommissionType),
        default=CommissionType.PERCENTAGE,
        nullable=False,
    )

    commission_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
    )

    total_clicks: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_referrals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    successful_referrals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    total_sales_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    total_commission_earned: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    total_commission_paid: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    updated_by: Mapped[str | None] = mapped_column(
        String(100),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=datetime.utcnow,
    )

    referrals = relationship(
        "AffiliateReferral",
        back_populates="affiliate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    commissions = relationship(
        "AffiliateCommission",
        back_populates="affiliate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    payouts = relationship(
        "AffiliatePayout",
        back_populates="affiliate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    coupons = relationship(
        "AffiliateCoupon",
        back_populates="affiliate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    clicks = relationship(
        "AffiliateClick",
        back_populates="affiliate",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "commission_value >= 0",
            name="ck_affiliate_commission_positive",
        ),
        Index("ix_affiliate_status", "status"),
        Index("ix_affiliate_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Affiliate("
            f"code={self.affiliate_code}, "
            f"status={self.status})>"
        )