"""Pydantic schemas for customer preferences (language, dark mode, marketing opt-in)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PreferenceUpdate(BaseModel):
    language: Optional[str] = Field(None, min_length=2, max_length=10)
    currency: Optional[str] = Field(None, min_length=3, max_length=10)
    dark_mode: Optional[bool] = None
    marketing_opt_in: Optional[bool] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


class PreferenceOut(BaseModel):
    id: UUID
    user_id: UUID
    language: str
    currency: str
    dark_mode: bool
    marketing_opt_in: bool
    email_notifications: bool
    sms_notifications: bool
    push_notifications: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
