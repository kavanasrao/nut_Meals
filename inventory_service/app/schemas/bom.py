"""Pydantic schemas for Bill of Materials."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BOMComponentIn(BaseModel):
    component_item_id: uuid.UUID
    quantity_required: float = Field(..., gt=0)


class BOMComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    component_item_id: uuid.UUID
    quantity_required: float


class BOMCreate(BaseModel):
    product_item_id: uuid.UUID
    yield_quantity: float = Field(default=1, gt=0)
    notes: str | None = None
    components: list[BOMComponentIn] = Field(..., min_length=1)


class BOMOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_item_id: uuid.UUID
    version: int
    yield_quantity: float
    is_active: bool
    notes: str | None
    components: list[BOMComponentOut]
    created_at: datetime


class BOMAvailabilityCheck(BaseModel):
    warehouse_id: uuid.UUID
    planned_quantity: float = Field(..., gt=0)


class BOMAvailabilityResult(BaseModel):
    is_available: bool
    shortfalls: list[dict]  # [{component_item_id, required, available}]
