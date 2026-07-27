"""
Affiliate Payout model.

Tracks payouts made to affiliates for approved commissions.
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
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PayoutStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PayoutMethod(str, enum.Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    PAYPAL = "PAYPAL"
    AMAZON_PAY = "AMAZON_PAY"
    STORE_CREDIT = "STORE_CREDIT"


class AffiliatePayout(Base):
    __tablename__ = "affiliate_payouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    affiliate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    payout_reference: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    payout_method: Mapped[PayoutMethod] = mapped_column(
        Enum(PayoutMethod),
        nullable=False,
    )

    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus),
        default=PayoutStatus.PENDING,
        nullable=False,
    )

    bank_reference: Mapped[str | None] = mapped_column(
        String(120),
    )

    transaction_reference: Mapped[str | None] = mapped_column(
        String(120),
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(100),
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    affiliate = relationship(
        "Affiliate",
        back_populates="payouts",
        lazy="joined",
    )

    commissions = relationship(
        "AffiliateCommission",
        back_populates="payout",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "amount >= 0",
            name="ck_aff_payout_amount_positive",
        ),
        Index("ix_aff_payout_status", "status"),
        Index("ix_aff_payout_paid_at", "paid_at"),
        Index("ix_aff_payout_reference", "payout_reference"),
    )

    def __repr__(self) -> str:
        return (
            f"<AffiliatePayout("
            f"reference={self.payout_reference}, "
            f"amount={self.amount}, "
            f"status={self.status})>"
        )