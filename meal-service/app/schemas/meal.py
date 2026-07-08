"""Pydantic schemas for the Meal Service."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.meal import MealCategory


# ── Requests ─────────────────────────────────────────────────────────────────

class MealCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    price: Decimal = Field(..., gt=Decimal("0"))
    category: str = Field(..., min_length=1, max_length=100)
    is_available: bool = True
    image_url: Optional[str] = Field(None, max_length=2048)
    nutrition_info: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    stock_count: int = Field(default=0, ge=0)
    max_daily_orders: Optional[int] = Field(None, ge=1)
    sort_order: int = Field(default=0, ge=0)
    is_featured: bool = False


class MealUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=Decimal("0"))
    category: Optional[str] = None
    is_available: Optional[bool] = None
    image_url: Optional[str] = None
    nutrition_info: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    stock_count: Optional[int] = Field(None, ge=0)
    max_daily_orders: Optional[int] = Field(None, ge=1)
    sort_order: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None


# ── Responses ─────────────────────────────────────────────────────────────────

class MealOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    price: Decimal
    category: str
    is_available: bool
    image_url: Optional[str] = None
    nutrition_info: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    stock_count: int
    max_daily_orders: Optional[int] = None
    sort_order: int
    is_featured: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MealListResponse(BaseModel):
    meals: list[MealOut]
    total: int
    limit: int
    offset: int
