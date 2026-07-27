"""Coupon engine — percent & fixed discount types."""
import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class DiscountType(str, enum.Enum):
    PERCENT = "percent"
    FIXED = "fixed"


class Coupon(Base, TimestampMixin):
    __tablename__ = "coupons"
    __table_args__ = (UniqueConstraint("code", name="uq_coupon_code"),)

    code = Column(String(64), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    discount_type = Column(Enum(DiscountType), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)

    # Constraints
    min_order_value = Column(Numeric(10, 2), nullable=True)   # Minimum cart total
    max_discount_cap = Column(Numeric(10, 2), nullable=True)  # Cap for percent discounts

    # Usage
    usage_limit = Column(Integer, nullable=True)              # None = unlimited
    usage_count = Column(Integer, default=0, nullable=False)
    per_user_limit = Column(Integer, default=1, nullable=False)

    # Validity
    is_active = Column(Boolean, default=True, nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=True)


class CouponUsage(Base, TimestampMixin):
    """Tracks which user has used a coupon, and how many times."""

    __tablename__ = "coupon_usages"
    __table_args__ = (
        UniqueConstraint("coupon_id", "user_id", name="uq_coupon_usage_user"),
    )

    coupon_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), nullable=True)
    times_used = Column(Integer, default=1, nullable=False)
