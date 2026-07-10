"""Pydantic request/response schemas for sitemap endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.sitemap import ChangeFrequency, SitemapEntityType


class SitemapEntryIn(BaseModel):
    entity_type: SitemapEntityType
    entity_id: str = Field(..., max_length=128)
    loc: str
    lastmod: datetime
    changefreq: ChangeFrequency = ChangeFrequency.WEEKLY
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    is_active: bool = True


class SitemapEntryOut(SitemapEntryIn):
    model_config = ConfigDict(from_attributes=True)
    id: str


class SitemapRebuildRequest(BaseModel):
    entity_type: SitemapEntityType | None = None
    force: bool = False


class SitemapRebuildAccepted(BaseModel):
    task_id: str
    entity_type: str | None
    status: str = "queued"
