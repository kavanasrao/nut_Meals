"""
Pydantic schemas for Credit Notes.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =====================================================
# ENUMS
# =====================================================

class CreditNoteStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    APPLIED = "applied"
    CANCELLED = "cancelled"


class CreditNoteReason(str, Enum):
    RETURN = "return"
    DAMAGED_GOODS = "damaged_goods"
    PRICE_ADJUSTMENT = "price_adjustment"
    ORDER_CANCELLED = "order_cancelled"
    GOODWILL = "goodwill"
    OTHER = "other"


# =====================================================
# BASE
# =====================================================

class CreditNoteBase(BaseModel):
    order_reference: str = Field(..., max_length=100)

    gst_invoice_id: Optional[UUID] = None

    reason: CreditNoteReason

    taxable_amount_minor: int = Field(..., ge=0)

    cgst_amount_minor: int = Field(default=0, ge=0)

    sgst_amount_minor: int = Field(default=0, ge=0)

    igst_amount_minor: int = Field(default=0, ge=0)

    total_amount_minor: int = Field(..., ge=0)

    currency: str = "INR"

    notes: Optional[str] = None


# =====================================================
# CREATE
# =====================================================

class CreditNoteCreate(CreditNoteBase):
    credit_note_number: str
    created_by: str


# =====================================================
# UPDATE
# =====================================================

class CreditNoteUpdate(BaseModel):
    status: Optional[CreditNoteStatus] = None

    notes: Optional[str] = None

    refund_id: Optional[UUID] = None

    issued_by: Optional[str] = None


# =====================================================
# RESPONSE
# =====================================================

class CreditNoteResponse(CreditNoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    credit_note_number: str

    status: CreditNoteStatus

    journal_entry_id: Optional[UUID]

    refund_id: Optional[UUID]

    created_by: str

    issued_by: Optional[str]

    issued_at: Optional[datetime]

    created_at: datetime

    updated_at: datetime