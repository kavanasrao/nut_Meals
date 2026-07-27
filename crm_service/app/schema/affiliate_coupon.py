"""
Affiliate Coupon schemas.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CouponStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


class DiscountType(str, Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


# ==========================================================
# Base
# ==========================================================

class AffiliateCouponBase(BaseModel):
    affiliate_id: UUID

    coupon_code: str = Field(
        ...,
        max_length=40,
    )

    title: str = Field(
        ...,
        max_length=120,
    )

    discount_type: DiscountType

    discount_value: Decimal = Field(
        ...,
        ge=0,
    )

    minimum_order_amount: int = Field(
        default=0,
        ge=0,
    )

    maximum_discount_amount: int | None = Field(
        default=None,
        ge=0,
    )

    usage_limit: int | None = Field(
        default=None,
        ge=1,
    )

    is_public: bool = False

    valid_from: datetime

    valid_until: datetime


# ==========================================================
# Create
# ==========================================================

class AffiliateCouponCreate(AffiliateCouponBase):
    created_by: str = Field(
        ...,
        max_length=100,
    )


# ==========================================================
# Update
# ==========================================================

class AffiliateCouponUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=120,
    )

    discount_type: DiscountType | None = None

    discount_value: Decimal | None = Field(
        default=None,
        ge=0,
    )

    minimum_order_amount: int | None = Field(
        default=None,
        ge=0,
    )

    maximum_discount_amount: int | None = Field(
        default=None,
        ge=0,
    )

    usage_limit: int | None = Field(
        default=None,
        ge=1,
    )

    status: CouponStatus | None = None

    is_public: bool | None = None

    valid_from: datetime | None = None

    valid_until: datetime | None = None


# ==========================================================
# Response
# ==========================================================

class AffiliateCouponResponse(AffiliateCouponBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    status: CouponStatus

    usage_count: int

    created_by: str

    created_at: datetime

    updated_at: datetime | None