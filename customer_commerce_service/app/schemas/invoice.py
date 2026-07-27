"""Invoice schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel
from app.models.invoice import InvoiceStatus


class InvoiceLineItem(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal


class InvoiceCreateRequest(BaseModel):
    order_id: UUID
    billing_name: str
    billing_address: str
    billing_gstin: Optional[str] = None
    subtotal: Decimal
    discount_amount: Decimal = Decimal("0")
    line_items: List[InvoiceLineItem]
    # Tax rates override (defaults from config)
    cgst_rate: Decimal = Decimal("9")
    sgst_rate: Decimal = Decimal("9")
    igst_rate: Decimal = Decimal("0")


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_number: str
    order_id: UUID
    user_id: UUID
    billing_name: str
    billing_address: str
    billing_gstin: Optional[str]
    subtotal: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    status: InvoiceStatus
    pdf_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
