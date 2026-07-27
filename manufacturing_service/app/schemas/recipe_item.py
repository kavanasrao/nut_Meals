"""
Recipe Item Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecipeItemBase(BaseModel):
    recipe_id: UUID
    raw_material_id: str
    quantity: Decimal
    unit: str
    wastage_percent: Decimal = Decimal("0.00")
    sequence: int = 1


class RecipeItemCreate(RecipeItemBase):
    pass


class RecipeItemUpdate(BaseModel):
    raw_material_id: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    wastage_percent: Decimal | None = None
    sequence: int | None = None


class RecipeItemResponse(RecipeItemBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)