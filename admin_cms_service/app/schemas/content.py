"""Pydantic schemas for the Content/Blog Manager API."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import ContentStatus, ContentType


class ContentItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None

    seo_title: Optional[str] = Field(None, max_length=70)
    seo_description: Optional[str] = Field(None, max_length=160)
    seo_keywords: Optional[list[str]] = None
    og_image_url: Optional[str] = Field(None, max_length=500)
    canonical_url: Optional[str] = Field(None, max_length=500)


class ContentItemCreate(ContentItemBase):
    content_type: ContentType
    slug: str = Field(..., min_length=1, max_length=255)
    publish_at: Optional[datetime] = None

    @field_validator("slug")
    @classmethod
    def slug_must_be_url_safe(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("slug must be lowercase, alphanumeric, and hyphen-separated")
        return v


class ContentItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    body: Optional[str] = Field(None, min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    tags: Optional[list[str]] = None
    status: Optional[ContentStatus] = None
    publish_at: Optional[datetime] = None
    seo_title: Optional[str] = Field(None, max_length=70)
    seo_description: Optional[str] = Field(None, max_length=160)
    seo_keywords: Optional[list[str]] = None
    og_image_url: Optional[str] = Field(None, max_length=500)
    canonical_url: Optional[str] = Field(None, max_length=500)


class ContentItemResponse(ContentItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_type: ContentType
    slug: str
    status: ContentStatus
    publish_at: Optional[datetime]
    published_at: Optional[datetime]
    author_admin_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ContentItemListResponse(BaseModel):
    items: list[ContentItemResponse]
    total: int
    page: int
    page_size: int
