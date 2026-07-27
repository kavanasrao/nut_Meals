from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.blog_category import BlogCategory


class BlogStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    excerpt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    featured_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    category_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("blog_categories.id"),
        nullable=False,
    )

    seo_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    seo_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    seo_keywords: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    author: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[BlogStatus] = mapped_column(
        Enum(BlogStatus),
        nullable=False,
        default=BlogStatus.DRAFT,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category: Mapped["BlogCategory"] = relationship(
        back_populates="posts",
    )