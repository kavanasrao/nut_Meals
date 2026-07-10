"""
ORM models for the Content/Blog Manager feature: blog posts, announcements,
and FAQs, with SEO metadata and scheduling support.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import ContentStatus, ContentType, TimestampMixin, UUIDPrimaryKeyMixin


class ContentItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A unit of manageable content: a blog post, announcement, or FAQ entry.

    Uses a single-table design (`content_type` discriminator) since all
    three content kinds share the same CRUD/scheduling/SEO shape; FAQs
    simply leave scheduling fields null.
    """

    __tablename__ = "content_items"
    __table_args__ = (
        Index("ix_content_items_status_publish_at", "status", "publish_at"),
        Index("ix_content_items_slug", "slug", unique=True),
    )

    content_type: Mapped[ContentType] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    status: Mapped[ContentStatus] = mapped_column(default=ContentStatus.DRAFT, nullable=False)

    # Scheduling
    publish_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # SEO metadata
    seo_title: Mapped[Optional[str]] = mapped_column(String(70), nullable=True)
    seo_description: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    seo_keywords: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    og_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Authoring
    author_admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    revisions: Mapped[list["ContentRevision"]] = relationship(
        back_populates="content_item", cascade="all, delete-orphan"
    )


class ContentRevision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable snapshot of a ContentItem body/title at edit time, for audit/history."""

    __tablename__ = "content_revisions"

    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_by_admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    content_item: Mapped["ContentItem"] = relationship(back_populates="revisions")
