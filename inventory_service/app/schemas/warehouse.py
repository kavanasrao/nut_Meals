"""Pydantic request/response schemas for warehouses, items and stock."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=128)
    location: str = Field(..., max_length=256)
    capacity_units: float = Field(default=0, ge=0)


class WarehouseUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    capacity_units: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    location: str
    capacity_units: float
    is_active: bool
    created_at: datetime


class ItemCreate(BaseModel):
    sku: str = Field(..., max_length=64)
    name: str = Field(..., max_length=256)
    unit_of_measure: str = Field(default="unit", max_length=16)
    is_finished_product: bool = False
    reorder_threshold: float = Field(default=0, ge=0)


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    sku: str
    name: str
    unit_of_measure: str
    is_finished_product: bool
    reorder_threshold: float


class StockLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    warehouse_id: uuid.UUID
    item_id: uuid.UUID
    quantity_on_hand: float
    quantity_reserved: float

    @property
    def quantity_available(self) -> float:
        return self.quantity_on_hand - self.quantity_reserved


class StockAdjustment(BaseModel):
    """Manual inbound/adjustment of stock at a warehouse."""
    item_id: uuid.UUID
    quantity_delta: float
    lot_number: str | None = None
    notes: str | None = None


class TransferCreate(BaseModel):
    item_id: uuid.UUID
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    lot_number: str | None = None


class TransferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    item_id: uuid.UUID
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    quantity: float
    lot_number: str | None
    status: str
    created_at: datetime
