"""
Pydantic schemas for Recipe Content.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.recipe import (
    DifficultyLevel,
    RecipeStatus,
)


class RecipeCreate(BaseModel):
    title: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)

    description: str | None = None

    ingredients: str
    instructions: str

    prep_time: int = Field(..., ge=0)
    cook_time: int = Field(..., ge=0)
    servings: int = Field(..., gt=0)

    difficulty: DifficultyLevel = DifficultyLevel.EASY

    calories: Decimal | None = None
    protein: Decimal | None = None
    carbohydrates: Decimal | None = None
    fats: Decimal | None = None

    featured_image: str | None = Field(
        default=None,
        max_length=500,
    )

    seo_title: str | None = Field(
        default=None,
        max_length=255,
    )

    seo_description: str | None = None

    seo_keywords: str | None = Field(
        default=None,
        max_length=500,
    )


class RecipeUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=255,
    )

    slug: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    ingredients: str | None = None
    instructions: str | None = None

    prep_time: int | None = Field(
        default=None,
        ge=0,
    )

    cook_time: int | None = Field(
        default=None,
        ge=0,
    )

    servings: int | None = Field(
        default=None,
        gt=0,
    )

    difficulty: DifficultyLevel | None = None

    calories: Decimal | None = None
    protein: Decimal | None = None
    carbohydrates: Decimal | None = None
    fats: Decimal | None = None

    featured_image: str | None = Field(
        default=None,
        max_length=500,
    )

    seo_title: str | None = Field(
        default=None,
        max_length=255,
    )

    seo_description: str | None = None

    seo_keywords: str | None = Field(
        default=None,
        max_length=500,
    )

    status: RecipeStatus | None = None


class RecipeOut(BaseModel):
    id: UUID

    title: str
    slug: str
    description: str | None

    ingredients: str
    instructions: str

    prep_time: int
    cook_time: int
    servings: int

    difficulty: DifficultyLevel

    calories: Decimal | None
    protein: Decimal | None
    carbohydrates: Decimal | None
    fats: Decimal | None

    featured_image: str | None

    seo_title: str | None
    seo_description: str | None
    seo_keywords: str | None

    status: RecipeStatus

    published_at: datetime | None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )