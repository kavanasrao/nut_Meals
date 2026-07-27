import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.base import InvoiceStatus


class PurchaseInvoiceItemCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class PurchaseInvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    description: Optional[str]
    quantity: int
    unit_price: Decimal
    tax_rate_percent: Decimal
    line_total: Decimal


class PurchaseInvoiceCreate(BaseModel):
    invoice_number: str = Field(..., min_length=1, max_length=100)
    vendor_id: uuid.UUID
    purchase_order_id: Optional[uuid.UUID] = None
    grn_id: Optional[uuid.UUID] = None
    invoice_date: date
    due_date: Optional[date] = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    file_url: Optional[str] = None
    items: list[PurchaseInvoiceItemCreate] = Field(..., min_length=1)


class PurchaseInvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus
    reconciliation_notes: Optional[str] = None


class PurchaseInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    vendor_id: uuid.UUID
    purchase_order_id: Optional[uuid.UUID]
    grn_id: Optional[uuid.UUID]
    status: InvoiceStatus
    invoice_date: date
    due_date: Optional[date]
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    file_url: Optional[str]
    reconciliation_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseInvoiceItemRead] = []


class PurchaseInvoiceListResponse(BaseModel):
    items: list[PurchaseInvoiceRead]
    total: int
    page: int
    page_size: int
