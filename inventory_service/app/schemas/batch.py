"""Pydantic schemas for production batches."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.batch import BatchStatus


class BatchCreate(BaseModel):
    bom_id: uuid.UUID
    warehouse_id: uuid.UUID
    planned_quantity: float = Field(..., gt=0)
    lot_number: str = Field(..., max_length=64)
    scheduled_start: datetime | None = None


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    batch_number: str
    bom_id: uuid.UUID
    warehouse_id: uuid.UUID
    planned_quantity: float
    actual_yield_quantity: float | None
    lot_number: str
    status: BatchStatus
    scheduled_start: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: str
    created_at: datetime


class BatchStatusUpdate(BaseModel):
    status: BatchStatus
    actual_yield_quantity: float | None = Field(default=None, ge=0)
