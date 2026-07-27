"""
Affiliate Commission model.

Stores commissions earned by affiliates from successful referrals.
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
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CommissionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class AffiliateCommission(Base):
    __tablename__ = "affiliate_commissions"

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

    referral_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "affiliate_referrals.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    sales_amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    commission_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )

    commission_amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
    )

    status: Mapped[CommissionStatus] = mapped_column(
        Enum(CommissionStatus),
        default=CommissionStatus.PENDING,
        nullable=False,
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(100),
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    payout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "affiliate_payouts.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
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
        back_populates="commissions",
        lazy="joined",
    )

    referral = relationship(
        "AffiliateReferral",
        lazy="joined",
    )

    payout = relationship(
        "AffiliatePayout",
        back_populates="commissions",
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint(
            "sales_amount >= 0",
            name="ck_aff_comm_sales_positive",
        ),
        CheckConstraint(
            "commission_amount >= 0",
            name="ck_aff_comm_amount_positive",
        ),
        CheckConstraint(
            "commission_rate >= 0",
            name="ck_aff_comm_rate_positive",
        ),
        Index("ix_aff_comm_status", "status"),
        Index("ix_aff_comm_created", "created_at"),
        Index("ix_aff_comm_order", "order_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AffiliateCommission("
            f"affiliate={self.affiliate_id}, "
            f"amount={self.commission_amount}, "
            f"status={self.status})>"
        )