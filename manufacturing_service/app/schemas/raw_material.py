"""
Pydantic schemas for Raw Material.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.raw_material import (
    RawMaterialStatus,
    UnitOfMeasure,
)


class RawMaterialCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    category: str
    supplier_id: str | None = None
    unit: UnitOfMeasure
    minimum_stock: Decimal
    reorder_level: Decimal
    reorder_quantity: Decimal
    unit_cost: Decimal
    gst_rate: Decimal
    warehouse_id: str | None = None
    is_perishable: bool = False
    shelf_life_days: int | None = None


class RawMaterialUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    minimum_stock: Decimal | None = None
    reorder_level: Decimal | None = None
    reorder_quantity: Decimal | None = None
    unit_cost: Decimal | None = None
    status: RawMaterialStatus | None = None


class RawMaterialOut(BaseModel):
    id: UUID
    code: str
    name: str
    category: str
    unit: UnitOfMeasure
    current_stock: Decimal
    reserved_stock: Decimal
    minimum_stock: Decimal
    reorder_level: Decimal
    reorder_quantity: Decimal
    unit_cost: Decimal
    gst_rate: Decimal
    status: RawMaterialStatus
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }