"""Pydantic schemas for redirect and canonical URL management endpoints."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.redirects import RedirectType


class RedirectRuleIn(BaseModel):
    source_path: str = Field(..., max_length=2048)
    target_path: str = Field(..., max_length=2048)
    redirect_type: RedirectType = RedirectType.PERMANENT
    reason: str | None = None
    is_active: bool = True


class RedirectRuleOut(RedirectRuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    hit_count: int
    synced_from_catalog: bool
    created_at: datetime
    updated_at: datetime


class RedirectLookupOut(BaseModel):
    source_path: str
    target_path: str
    redirect_type: int


class CanonicalUrlIn(BaseModel):
    entity_type: str
    entity_id: str
    canonical_path: str
    notes: str | None = None


class CanonicalUrlOut(CanonicalUrlIn):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
