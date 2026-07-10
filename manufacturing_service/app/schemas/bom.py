"""
Pydantic schemas for BOM.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.bom import BOMStatus


class BOMItemCreate(BaseModel):
    raw_material_id: UUID
    quantity: Decimal
    wastage_percent: Decimal = Decimal("0")


class BOMCreate(BaseModel):
    product_id: str
    product_name: str
    version: str = "1.0"
    created_by: str
    notes: str | None = None
    items: list[BOMItemCreate]


class BOMOut(BaseModel):
    id: UUID
    product_id: str
    product_name: str
    version: str
    status: BOMStatus
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
    