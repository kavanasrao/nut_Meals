"""
Pydantic schemas for the Returns API.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.return_request import (
    ReturnResolution,
    ReturnStatus,
    ReturnTier,
)


# ==========================================================
# Return Item
# ==========================================================

class ReturnItemCreate(BaseModel):
    order_item_id: str
    product_id: str
    product_name: str
    sku: str
    quantity: int = Field(..., gt=0)
    unit_price: Decimal
    refund_amount: Decimal


class ReturnItemOut(ReturnItemCreate):
    id: UUID

    model_config = {
        "from_attributes": True
    }


# ==========================================================
# Create Return Request
# ==========================================================

class ReturnCreate(BaseModel):

    order_id: str

    user_id: str

    reason: str = Field(
        ...,
        min_length=5,
        max_length=500,
    )

    tier: ReturnTier

    items: list[ReturnItemCreate]


# ==========================================================
# Update Return
# ==========================================================

class ReturnUpdate(BaseModel):

    status: Optional[ReturnStatus] = None

    resolution: Optional[ReturnResolution] = None


# ==========================================================
# Return Response
# ==========================================================

class ReturnOut(BaseModel):

    id: UUID

    order_id: str

    user_id: str

    reason: str

    tier: ReturnTier

    status: ReturnStatus

    resolution: Optional[ReturnResolution]

    created_at: datetime

    updated_at: datetime

    items: list[ReturnItemOut] = []

    model_config = {
        "from_attributes": True
    }


# ==========================================================
# Return Decision
# ==========================================================

class ReturnDecision(BaseModel):

    resolution: ReturnResolution

    remarks: Optional[str] = Field(
        None,
        max_length=500,
    )