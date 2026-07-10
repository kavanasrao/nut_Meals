"""
Pydantic schemas for Production Batch.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.production_batch import BatchStatus


class ProductionBatchCreate(BaseModel):
    batch_number: str
    product_id: str
    bom_id: UUID
    planned_quantity: Decimal


class ProductionBatchOut(BaseModel):
    id: UUID
    batch_number: str
    product_id: str
    planned_quantity: Decimal
    produced_quantity: Decimal
    status: BatchStatus
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
    