"""
Pydantic schemas for Blog Posts.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.blog_post import BlogStatus


class BlogPostCreate(BaseModel):
    title: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    excerpt: str | None = None
    content: str
    featured_image: str | None = Field(default=None, max_length=500)

    category_id: UUID

    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = None
    seo_keywords: str | None = Field(default=None, max_length=500)

    author: str = Field(..., max_length=100)


class BlogPostUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    excerpt: str | None = None
    content: str | None = None
    featured_image: str | None = Field(default=None, max_length=500)

    category_id: UUID | None = None

    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = None
    seo_keywords: str | None = Field(default=None, max_length=500)

    author: str | None = Field(default=None, max_length=100)

    status: BlogStatus | None = None


class BlogPostOut(BaseModel):
    id: UUID

    title: str
    slug: str
    excerpt: str | None
    content: str
    featured_image: str | None

    category_id: UUID

    seo_title: str | None
    seo_description: str | None
    seo_keywords: str | None

    author: str

    status: BlogStatus

    published_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)