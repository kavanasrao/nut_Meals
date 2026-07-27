"""
Recipe Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.recipe import RecipeStatus


class RecipeBase(BaseModel):
    recipe_code: str
    product_id: str
    version: int = 1
    description: str | None = None
    status: RecipeStatus = RecipeStatus.DRAFT


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    recipe_code: str | None = None
    product_id: str | None = None
    version: int | None = None
    description: str | None = None
    status: RecipeStatus | None = None


class RecipeResponse(RecipeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)