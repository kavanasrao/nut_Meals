"""Pydantic request/response schemas for subscription lifecycle endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.subscription import SubscriptionFrequency, SubscriptionStatus


class SubscriptionCreate(BaseModel):
    plan_id: str = Field(..., max_length=64)
    plan_snapshot: dict = Field(default_factory=dict)
    frequency: SubscriptionFrequency
    price_amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    payment_method_token: str = Field(..., max_length=255)
    shipping_address_id: uuid.UUID
    start_date: datetime | None = None


class SubscriptionPauseRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class SubscriptionCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_id: uuid.UUID
    plan_id: str
    frequency: SubscriptionFrequency
    status: SubscriptionStatus
    price_amount: float
    currency: str
    next_renewal_date: datetime
    last_renewed_at: datetime | None
    failed_renewal_attempts: int
    paused_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime
