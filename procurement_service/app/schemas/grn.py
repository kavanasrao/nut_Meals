import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import GRNStatus


class GRNItemCreate(BaseModel):
    purchase_order_item_id: uuid.UUID
    sku: str = Field(..., min_length=1, max_length=100)
    quantity_received: int = Field(..., ge=0)
    quantity_rejected: int = Field(default=0, ge=0)
    rejection_reason: Optional[str] = None


class GRNItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_item_id: uuid.UUID
    sku: str
    quantity_received: int
    quantity_rejected: int
    rejection_reason: Optional[str]


class GRNCreate(BaseModel):
    purchase_order_id: uuid.UUID
    remarks: Optional[str] = None
    items: list[GRNItemCreate] = Field(..., min_length=1)


class GRNRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    grn_number: str
    purchase_order_id: uuid.UUID
    status: GRNStatus
    received_by: uuid.UUID
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: list[GRNItemRead] = []


class GRNListResponse(BaseModel):
    items: list[GRNRead]
    total: int
    page: int
    page_size: int
