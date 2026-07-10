"""
Shared enums and mixins used across Admin CMS ORM models.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Adds created_at / updated_at columns to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key column named `id`."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class ReturnStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class ReturnTier(str, enum.Enum):
    """Resolution tiers for returns, from lowest to highest severity/effort."""
    A = "A"  # simple refund / auto-approved
    B = "B"  # requires inspection or partial refund
    C = "C"  # escalated, requires manual investigation / logistics involvement


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentType(str, enum.Enum):
    BLOG_POST = "blog_post"
    ANNOUNCEMENT = "announcement"
    FAQ = "faq"


class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    FINANCE_ADMIN = "finance_admin"
    CONTENT_ADMIN = "content_admin"
    SUPPORT_ADMIN = "support_admin"
    ANALYTICS_VIEWER = "analytics_viewer"
