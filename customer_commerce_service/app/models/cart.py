"""Cart + CartItem models."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class Cart(Base, TimestampMixin):
    __tablename__ = "carts"

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_activity_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    recovery_email_sent_at = Column(DateTime(timezone=True), nullable=True)
    coupon_code = Column(String(64), nullable=True)

    # selectin = always load items in the same SELECT (async-safe, no lazy greenlet)
    items = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"

    cart_id = Column(
        UUID(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = Column(UUID(as_uuid=True), nullable=False)
    product_name = Column(String(255), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    image_url = Column(String(512), nullable=True)

    cart = relationship("Cart", back_populates="items", lazy="selectin")
