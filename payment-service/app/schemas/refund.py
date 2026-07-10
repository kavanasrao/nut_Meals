"""
Pydantic schemas for Refund APIs.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.refund import RefundStatus


class RefundCreate(BaseModel):
    payment_id: UUID
    amount: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)
    reason: Optional[str] = Field(None, max_length=500)
    initiated_by: Optional[str] = Field(None, max_length=255)


class RefundOut(BaseModel):
    id: UUID
    payment_id: UUID
    amount: Decimal
    reason: Optional[str]
    provider_refund_id: Optional[str]
    status: RefundStatus
    initiated_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }