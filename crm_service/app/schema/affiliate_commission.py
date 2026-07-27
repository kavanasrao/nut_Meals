"""
Affiliate Commission schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommissionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ==========================================================
# Base
# ==========================================================

class AffiliateCommissionBase(BaseModel):
    affiliate_id: UUID
    referral_id: UUID
    order_id: UUID

    sales_amount: int = Field(..., ge=0)

    commission_rate: Decimal = Field(..., ge=0)

    commission_amount: int = Field(..., ge=0)

    currency: str = Field(default="INR", min_length=3, max_length=3)

    remarks: str | None = None


# ==========================================================
# Create
# ==========================================================

class AffiliateCommissionCreate(AffiliateCommissionBase):
    created_by: str = Field(..., max_length=100)


# ==========================================================
# Update
# ==========================================================

class AffiliateCommissionUpdate(BaseModel):
    status: CommissionStatus | None = None

    approved_by: str | None = Field(
        default=None,
        max_length=100,
    )

    approved_at: datetime | None = None

    payout_id: UUID | None = None

    remarks: str | None = None


# ==========================================================
# Response
# ==========================================================

class AffiliateCommissionResponse(AffiliateCommissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    status: CommissionStatus

    approved_by: str | None

    approved_at: datetime | None

    payout_id: UUID | None

    created_by: str

    created_at: datetime

    updated_at: datetime | None