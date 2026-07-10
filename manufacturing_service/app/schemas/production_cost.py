"""
Pydantic schemas for Production Cost.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ProductionCostCreate(BaseModel):
    batch_id: UUID
    material_cost: Decimal
    labour_cost: Decimal
    overhead_cost: Decimal


class ProductionCostOut(BaseModel):
    id: UUID
    batch_id: UUID
    material_cost: Decimal
    labour_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal

    model_config = {
        "from_attributes": True,
    }
    