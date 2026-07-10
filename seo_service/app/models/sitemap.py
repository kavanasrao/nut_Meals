"""
Models backing the dynamic sitemap feature.

`SitemapEntry` is a denormalized, service-local cache of URLs pulled
from Catalog/Blog services. It is rebuilt incrementally by Celery tasks
whenever upstream products/categories/posts change (via webhook or
polling), so sitemap generation never has to call out synchronously to
another service on a user-facing request.

`SitemapFile` tracks generated physical sitemap XML files (products,
categories, blogs) plus the parent sitemap index, so we can serve
pre-rendered XML and paginate beyond Google's 50,000-URL limit.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SitemapEntityType(str, enum.Enum):
    PRODUCT = "product"
    CATEGORY = "category"
    BLOG_POST = "blog_post"
    STATIC_PAGE = "static_page"


class ChangeFrequency(str, enum.Enum):
    ALWAYS = "always"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    NEVER = "never"


class SitemapEntry(Base):
    """A single <url> entry that belongs in one of the sitemap files."""

    __tablename__ = "sitemap_entries"
    __table_args__ = (
        Index("ix_sitemap_entries_entity", "entity_type", "entity_id", unique=True),
        Index("ix_sitemap_entries_type_updated", "entity_type", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[SitemapEntityType] = mapped_column(
        Enum(SitemapEntityType, name="sitemap_entity_type"), nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    loc: Mapped[str] = mapped_column(Text, nullable=False)
    lastmod: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    changefreq: Mapped[ChangeFrequency] = mapped_column(
        Enum(ChangeFrequency, name="sitemap_changefreq"),
        default=ChangeFrequency.WEEKLY,
        nullable=False,
    )
    priority: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SitemapFile(Base):
    """A generated, cached sitemap XML file (a leaf file or the index)."""

    __tablename__ = "sitemap_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    # e.g. "sitemap-products-1.xml", "sitemap-index.xml"
    entity_type: Mapped[SitemapEntityType | None] = mapped_column(
        Enum(SitemapEntityType, name="sitemap_entity_type"), nullable=True
    )
    part_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    url_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xml_content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
