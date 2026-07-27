"""
Pydantic schemas for Refunds.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =====================================================
# ENUMS
# =====================================================

class RefundStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RefundMethod(str, Enum):
    ORIGINAL_PAYMENT = "original_payment"
    BANK_TRANSFER = "bank_transfer"
    STORE_CREDIT = "store_credit"
    CASH = "cash"
    OTHER = "other"


# =====================================================
# BASE
# =====================================================

class RefundBase(BaseModel):
    order_reference: str = Field(..., max_length=100)

    refund_amount_minor: int = Field(..., ge=0)

    currency: str = "INR"

    method: RefundMethod

    reason: Optional[str] = None


# =====================================================
# CREATE
# =====================================================

class RefundCreate(RefundBase):
    created_by: str


# =====================================================
# UPDATE
# =====================================================

class RefundUpdate(BaseModel):
    status: Optional[RefundStatus] = None

    gateway_refund_id: Optional[str] = None

    completed_at: Optional[datetime] = None


# =====================================================
# RESPONSE
# =====================================================

class RefundResponse(RefundBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    status: RefundStatus

    gateway_refund_id: Optional[str]

    journal_entry_id: Optional[UUID]

    created_by: str

    created_at: datetime

    updated_at: datetime

    completed_at: Optional[datetime]