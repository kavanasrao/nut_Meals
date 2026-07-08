"""Pydantic schemas for the User Service."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


# ── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^\+?\d{7,15}$")
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    role: UserRole
    is_blocked: bool
    is_verified: bool
    profile_picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, pattern=r"^\+?\d{7,15}$")
    bio: Optional[str] = Field(None, max_length=500)
    profile_picture: Optional[str] = Field(None, max_length=2048)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Pagination / stats ────────────────────────────────────────────────────────

class UserListResponse(BaseModel):
    users: list[UserOut]
    total: int
    limit: int
    offset: int


class UserStatsResponse(BaseModel):
    total: int
    active: int
    blocked: int
