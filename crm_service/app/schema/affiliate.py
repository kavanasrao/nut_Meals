"""
Affiliate schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AffiliateStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BLOCKED = "BLOCKED"


class CommissionType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


# ==========================================================
# Base
# ==========================================================

class AffiliateBase(BaseModel):
    customer_id: UUID
    affiliate_code: str = Field(..., max_length=40)
    display_name: str = Field(..., max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)

    commission_type: CommissionType = CommissionType.PERCENTAGE
    commission_value: Decimal = Field(..., ge=0)

    notes: str | None = None


# ==========================================================
# Create
# ==========================================================

class AffiliateCreate(AffiliateBase):
    created_by: str = Field(..., max_length=100)


# ==========================================================
# Update
# ==========================================================

class AffiliateUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)

    status: AffiliateStatus | None = None

    commission_type: CommissionType | None = None
    commission_value: Decimal | None = Field(default=None, ge=0)

    notes: str | None = None

    updated_by: str = Field(..., max_length=100)


# ==========================================================
# Response
# ==========================================================

class AffiliateResponse(AffiliateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    status: AffiliateStatus

    total_clicks: int
    total_referrals: int
    successful_referrals: int

    total_sales_amount: int
    total_commission_earned: int
    total_commission_paid: int

    is_verified: bool

    created_by: str
    updated_by: str | None

    created_at: datetime
    updated_at: datetime | None