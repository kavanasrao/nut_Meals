"""Pydantic schemas for the Delivery Service."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeliveryOption(BaseModel):
    """A single available delivery method returned by GET /delivery/options."""
    type: str                    # "pickup" | "home_delivery"
    available: bool
    eta: str                     # human-readable, e.g. "10 mins"
    eta_minutes: int
    reason_unavailable: Optional[str] = None  # populated when available=False


class DeliveryOptionsResponse(BaseModel):
    options: list[DeliveryOption]
    location: str


class DeliveryAssignmentOut(BaseModel):
    id: UUID
    order_id: str
    user_id: str
    delivery_type: str
    rider_name: Optional[str] = None
    rider_phone: Optional[str] = None
    status: str
    eta_minutes: Optional[int] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
