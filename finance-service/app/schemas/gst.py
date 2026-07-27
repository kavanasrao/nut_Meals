"""
Pydantic schemas for GST rate cards and GST invoices.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =====================================================
# GST RATE
# =====================================================

class GSTRateBase(BaseModel):
    category_code: str = Field(..., max_length=50)
    category_name: str = Field(..., max_length=120)
    hsn_code: Optional[str] = Field(None, max_length=20)
    rate_basis_points: int = Field(..., ge=0, le=10000)
    effective_from: str
    effective_to: Optional[str] = None
    is_active: bool = True


class GSTRateCreate(GSTRateBase):
    created_by: str


class GSTRateUpdate(BaseModel):
    category_name: Optional[str] = None
    hsn_code: Optional[str] = None
    rate_basis_points: Optional[int] = Field(None, ge=0, le=10000)
    effective_to: Optional[str] = None
    is_active: Optional[bool] = None


class GSTRateResponse(GSTRateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by: str
    created_at: datetime
    updated_at: datetime


# =====================================================
# GST INVOICE LINE
# =====================================================

class GSTInvoiceLineCreate(BaseModel):
    product_reference: Optional[str] = None
    category_code: str
    taxable_amount_minor: int = Field(..., ge=0)
    description: Optional[str] = None


class GSTInvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line_number: int
    product_reference: Optional[str]
    category_code: str

    taxable_amount_minor: int
    cgst_amount_minor: int
    sgst_amount_minor: int
    igst_amount_minor: int

    description: Optional[str]


# =====================================================
# GST INVOICE
# =====================================================

class GSTInvoiceCreate(BaseModel):
    invoice_number: str
    order_reference: str

    invoice_date: str

    seller_state_code: str
    customer_state_code: str

    created_by: str

    lines: List[GSTInvoiceLineCreate]


class GSTInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    invoice_number: str
    order_reference: str

    invoice_date: str

    seller_state_code: str
    customer_state_code: str
    is_interstate: bool

    taxable_amount_minor: int

    cgst_amount_minor: int
    sgst_amount_minor: int
    igst_amount_minor: int

    total_gst_amount_minor: int
    total_invoice_amount_minor: int

    currency: str

    status: str

    created_by: str
    posted_by: Optional[str]

    created_at: datetime
    updated_at: datetime

    lines: List[GSTInvoiceLineResponse]