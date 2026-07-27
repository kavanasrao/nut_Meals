"""Wishlist model — one entry per user/product pair."""
from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin


class WishlistItem(Base, TimestampMixin):
    __tablename__ = "wishlist_items"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )

    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    product_name = Column(String(255), nullable=False)
    image_url = Column(String(512), nullable=True)
    unit_price = Column(String(32), nullable=False)  # Stored as string to avoid currency drift
