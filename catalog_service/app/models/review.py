"""Customer review model with moderation workflow."""
import enum
import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Review(Base, UUIDPKMixin, TimestampMixin):
    """A customer review + rating, subject to moderation before publishing."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating_range"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(ReviewStatus, name="review_status"), default=ReviewStatus.PENDING, nullable=False
    )
    moderated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    moderation_notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    product: Mapped["Product"] = relationship(back_populates="reviews")


class ProductRatingAggregate(Base, UUIDPKMixin, TimestampMixin):
    """Denormalized aggregate rating per product, recomputed on moderation events."""

    __tablename__ = "product_rating_aggregates"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    average_rating: Mapped[float] = mapped_column(default=0.0, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
