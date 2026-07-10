"""
Models for schema.org JSON-LD structured data caching.

We cache the rendered JSON-LD per entity so the frontend can request it
with a single low-latency GET, and so we can validate/version schema
changes (e.g. Google Rich Results requirement updates) without
re-deriving from Catalog on every request.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SchemaType(str, enum.Enum):
    PRODUCT = "Product"
    REVIEW = "Review"
    AGGREGATE_RATING = "AggregateRating"
    BLOG_POSTING = "BlogPosting"
    BREADCRUMB_LIST = "BreadcrumbList"
    ORGANIZATION = "Organization"
    FAQ_PAGE = "FAQPage"


class StructuredDataRecord(Base):
    """Cached JSON-LD payload for a single entity + schema type."""

    __tablename__ = "structured_data_records"
    __table_args__ = (
        Index(
            "ix_structured_data_entity_schema",
            "entity_type",
            "entity_id",
            "schema_type",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "product" | "blog_post"
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_type: Mapped[SchemaType] = mapped_column(
        Enum(SchemaType, name="schema_type"), nullable=False
    )
    json_ld: Mapped[dict] = mapped_column(JSONB, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)
    is_valid: Mapped[bool] = mapped_column(default=True, nullable=False)
    validation_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
