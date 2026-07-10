"""Pydantic schemas for redirect management."""
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class RedirectCreate(BaseModel):
    source_path: str = Field(..., max_length=500)
    target_path: str = Field(..., max_length=500)
    redirect_type: Literal[301, 302] = 301
    is_active: bool = True
    notes: Optional[str] = Field(None, max_length=500)


class RedirectUpdate(BaseModel):
    target_path: Optional[str] = Field(None, max_length=500)
    redirect_type: Optional[Literal[301, 302]] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)


class RedirectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_path: str
    target_path: str
    redirect_type: int
    is_active: bool
    notes: Optional[str]


class RedirectResolveResponse(BaseModel):
    found: bool
    target_path: Optional[str] = None
    redirect_type: Optional[int] = None
