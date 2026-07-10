"""SEO metadata model, one-to-one with Product."""
import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class SEOMetadata(Base, UUIDPKMixin, TimestampMixin):
    """SEO fields + JSON-LD structured data for a product's storefront page."""

    __tablename__ = "seo_metadata"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    meta_title: Mapped[Optional[str]] = mapped_column(String(70), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    meta_keywords: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    og_title: Mapped[Optional[str]] = mapped_column(String(95), nullable=True)
    og_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    og_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # schema.org Product structured data, stored as JSON-LD ready for embedding
    structured_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    product: Mapped["Product"] = relationship(back_populates="seo_metadata")
