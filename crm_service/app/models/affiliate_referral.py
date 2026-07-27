"""
Affiliate Referral model.

Tracks every customer referred by an affiliate.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ReferralStatus(str, enum.Enum):
    PENDING = "PENDING"
    REGISTERED = "REGISTERED"
    FIRST_ORDER = "FIRST_ORDER"
    QUALIFIED = "QUALIFIED"
    REWARDED = "REWARDED"
    CANCELLED = "CANCELLED"


class AffiliateReferral(Base):
    __tablename__ = "affiliate_referrals"

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

    referred_customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True,
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    referral_code: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    status: Mapped[ReferralStatus] = mapped_column(
        Enum(ReferralStatus),
        default=ReferralStatus.PENDING,
        nullable=False,
    )

    order_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    commission_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    referred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    affiliate = relationship(
        "Affiliate",
        back_populates="referrals",
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint(
            "order_amount >= 0",
            name="ck_referral_order_amount_positive",
        ),
        CheckConstraint(
            "commission_amount >= 0",
            name="ck_referral_commission_positive",
        ),
        Index("ix_referral_status", "status"),
        Index("ix_referral_date", "referred_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AffiliateReferral("
            f"affiliate={self.affiliate_id}, "
            f"customer={self.referred_customer_id})>"
        )