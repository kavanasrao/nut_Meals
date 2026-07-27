"""
Affiliate Payout schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PayoutStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PayoutMethod(str, Enum):
    BANK_TRANSFER = "BANK_TRANSFER"
    UPI = "UPI"
    PAYPAL = "PAYPAL"
    AMAZON_PAY = "AMAZON_PAY"
    STORE_CREDIT = "STORE_CREDIT"


# ==========================================================
# Base
# ==========================================================

class AffiliatePayoutBase(BaseModel):
    affiliate_id: UUID

    payout_reference: str = Field(
        ...,
        max_length=50,
    )

    payout_method: PayoutMethod

    amount: int = Field(..., ge=0)

    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
    )

    bank_reference: str | None = Field(
        default=None,
        max_length=120,
    )

    transaction_reference: str | None = Field(
        default=None,
        max_length=120,
    )

    failure_reason: str | None = None


# ==========================================================
# Create
# ==========================================================

class AffiliatePayoutCreate(AffiliatePayoutBase):
    requested_by: str = Field(
        ...,
        max_length=100,
    )


# ==========================================================
# Update
# ==========================================================

class AffiliatePayoutUpdate(BaseModel):
    status: PayoutStatus | None = None

    approved_by: str | None = Field(
        default=None,
        max_length=100,
    )

    approved_at: datetime | None = None

    paid_at: datetime | None = None

    bank_reference: str | None = Field(
        default=None,
        max_length=120,
    )

    transaction_reference: str | None = Field(
        default=None,
        max_length=120,
    )

    failure_reason: str | None = None


# ==========================================================
# Response
# ==========================================================

class AffiliatePayoutResponse(AffiliatePayoutBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    status: PayoutStatus

    requested_by: str

    approved_by: str | None

    approved_at: datetime | None

    paid_at: datetime | None

    created_at: datetime

    updated_at: datetime | None