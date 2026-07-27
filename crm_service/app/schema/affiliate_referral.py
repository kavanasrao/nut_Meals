"""
Affiliate Referral schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReferralStatus(str, Enum):
    PENDING = "PENDING"
    REGISTERED = "REGISTERED"
    FIRST_ORDER = "FIRST_ORDER"
    QUALIFIED = "QUALIFIED"
    REWARDED = "REWARDED"
    CANCELLED = "CANCELLED"


# ==========================================================
# Base
# ==========================================================

class AffiliateReferralBase(BaseModel):
    affiliate_id: UUID
    referred_customer_id: UUID

    order_id: UUID | None = None
    coupon_id: UUID | None = None

    referral_code: str = Field(..., max_length=40)

    order_amount: int = Field(default=0, ge=0)
    commission_amount: int = Field(default=0, ge=0)


# ==========================================================
# Create
# ==========================================================

class AffiliateReferralCreate(AffiliateReferralBase):
    created_by: str = Field(..., max_length=100)


# ==========================================================
# Update
# ==========================================================

class AffiliateReferralUpdate(BaseModel):
    order_id: UUID | None = None

    status: ReferralStatus | None = None

    order_amount: int | None = Field(default=None, ge=0)
    commission_amount: int | None = Field(default=None, ge=0)

    converted_at: datetime | None = None


# ==========================================================
# Response
# ==========================================================

class AffiliateReferralResponse(AffiliateReferralBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    status: ReferralStatus

    referred_at: datetime
    converted_at: datetime | None

    created_by: str