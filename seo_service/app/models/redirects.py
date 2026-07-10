"""
Models for redirect management and canonical URL enforcement.

`RedirectRule` mirrors/extends Catalog's redirect manager (e.g. when a
product slug changes) so the SEO service can serve a single source of
truth for 301/302 lookups without a network hop on every request.
`CanonicalUrl` records the canonical URL chosen per entity, to prevent
duplicate-content issues from filtered/paginated/tracking-param URLs.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RedirectType(int, enum.Enum):
    PERMANENT = 301
    TEMPORARY = 302


class RedirectRule(Base):
    """A single from-path -> to-path redirect rule."""

    __tablename__ = "redirect_rules"
    __table_args__ = (
        Index("ix_redirect_rules_source_path", "source_path", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    redirect_type: Mapped[RedirectType] = mapped_column(
        Integer, default=RedirectType.PERMANENT.value, nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    synced_from_catalog: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CanonicalUrl(Base):
    """The canonical URL declared for a given entity, to dedupe content."""

    __tablename__ = "canonical_urls"
    __table_args__ = (
        Index("ix_canonical_urls_entity", "entity_type", "entity_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    canonical_path: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
