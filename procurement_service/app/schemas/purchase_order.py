import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.base import PurchaseOrderStatus


class PurchaseOrderItemCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    quantity_ordered: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class PurchaseOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    description: Optional[str]
    quantity_ordered: int
    quantity_received: int
    unit_price: Decimal
    tax_rate_percent: Decimal
    line_total: Decimal


class PurchaseOrderCreate(BaseModel):
    vendor_id: uuid.UUID
    expected_delivery_date: Optional[date] = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    notes: Optional[str] = None
    items: list[PurchaseOrderItemCreate] = Field(..., min_length=1)

    @field_validator("items")
    @classmethod
    def unique_skus_not_required(cls, v):
        if not v:
            raise ValueError("At least one line item is required")
        return v


class PurchaseOrderUpdate(BaseModel):
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None


class PurchaseOrderApproval(BaseModel):
    approve: bool
    rejection_reason: Optional[str] = None

    @field_validator("rejection_reason")
    @classmethod
    def require_reason_on_reject(cls, v, info):
        if info.data.get("approve") is False and not v:
            raise ValueError("rejection_reason is required when rejecting a PO")
        return v


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    po_number: str
    vendor_id: uuid.UUID
    status: PurchaseOrderStatus
    expected_delivery_date: Optional[date]
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: Optional[str]
    created_by: uuid.UUID
    approved_by: Optional[uuid.UUID]
    approved_at: Optional[str]
    rejection_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseOrderItemRead] = []


class PurchaseOrderListResponse(BaseModel):
    items: list[PurchaseOrderRead]
    total: int
    page: int
    page_size: int
