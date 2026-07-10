"""Pydantic schemas for inventory reservations."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reservation import ReservationStatus


class ReservationCreate(BaseModel):
    order_id: str = Field(..., max_length=64)
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    ttl_seconds: int | None = Field(default=None, gt=0, description="Override default TTL")


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order_id: str
    item_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: float
    status: ReservationStatus
    expires_at: datetime
    confirmed_at: datetime | None
    released_at: datetime | None
    created_at: datetime
