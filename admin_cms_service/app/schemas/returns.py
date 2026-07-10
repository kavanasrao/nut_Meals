"""Pydantic schemas for the Returns Management API."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import ReturnStatus, ReturnTier


class ReturnRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: Optional[uuid.UUID]
    customer_id: uuid.UUID
    reason: str
    reason_detail: Optional[str]
    status: ReturnStatus
    tier: ReturnTier
    refund_amount: Optional[Decimal]
    restock_required: bool
    logistics_reference: Optional[str]
    decided_by_admin_id: Optional[uuid.UUID]
    decided_at: Optional[datetime]
    resolution_notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReturnRequestListResponse(BaseModel):
    items: list[ReturnRequestResponse]
    total: int
    page: int
    page_size: int


class ReturnDecisionRequest(BaseModel):
    """Body for approve/reject actions."""

    tier: ReturnTier = ReturnTier.A
    refund_amount: Optional[Decimal] = Field(None, ge=0)
    restock_required: bool = False
    resolution_notes: Optional[str] = Field(None, max_length=2000)


class ReturnEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: Optional[ReturnStatus]
    to_status: ReturnStatus
    actor_admin_id: Optional[uuid.UUID]
    notes: Optional[str]
    created_at: datetime
