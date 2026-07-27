"""
Pydantic schemas for Blog Category.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BlogCategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=120)
    description: str | None = None


class BlogCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = None


class BlogCategoryOut(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)