"""Pydantic schemas for the Payment Service."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment import PaymentStatus


class PaymentCreate(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    amount: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)
    email: Optional[str] = Field(None, max_length=320)
    phone: Optional[str] = Field(None, max_length=20)
    return_url: Optional[str] = Field(None, max_length=2048)


class PaymentOut(BaseModel):
    id: UUID
    order_id: str
    user_id: str
    provider: str
    provider_payment_id: Optional[str] = None
    provider_payment_url: Optional[str] = None
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class PaymentInitResponse(BaseModel):
    payment_id: UUID
    payment_url: str
    provider: str
    status: PaymentStatus
