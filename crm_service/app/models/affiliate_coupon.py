"""
Affiliate Coupon model.

Represents coupons assigned to affiliates for
tracking sales and commissions.
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
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CouponStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class AffiliateCoupon(Base):
    __tablename__ = "affiliate_coupons"

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

    coupon_code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType),
        nullable=False,
    )

    discount_value: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    minimum_order_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    maximum_discount_amount: Mapped[int | None] = mapped_column(
        BigInteger,
    )

    usage_limit: Mapped[int | None] = mapped_column(
        Integer,
    )

    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    status: Mapped[CouponStatus] = mapped_column(
        Enum(CouponStatus),
        default=CouponStatus.ACTIVE,
        nullable=False,
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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
        back_populates="coupons",
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint(
            "discount_value >= 0",
            name="ck_aff_coupon_discount_positive",
        ),
        CheckConstraint(
            "minimum_order_amount >= 0",
            name="ck_aff_coupon_min_order_positive",
        ),
        CheckConstraint(
            "usage_count >= 0",
            name="ck_aff_coupon_usage_positive",
        ),
        Index(
            "ix_aff_coupon_status",
            "status",
        ),
        Index(
            "ix_aff_coupon_valid_until",
            "valid_until",
        ),
        Index(
            "ix_aff_coupon_code",
            "coupon_code",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AffiliateCoupon("
            f"code={self.coupon_code}, "
            f"status={self.status})>"
        )