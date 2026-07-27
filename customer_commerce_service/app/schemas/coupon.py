"""Coupon request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from app.models.coupon import DiscountType


class CouponCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[A-Z0-9_\-]+$")
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: Decimal = Field(..., gt=0)
    min_order_value: Optional[Decimal] = None
    max_discount_cap: Optional[Decimal] = None
    usage_limit: Optional[int] = Field(None, ge=1)
    per_user_limit: int = Field(1, ge=1)
    valid_from: datetime
    valid_until: Optional[datetime] = None


class CouponResponse(BaseModel):
    id: UUID
    code: str
    description: Optional[str]
    discount_type: DiscountType
    discount_value: Decimal
    min_order_value: Optional[Decimal]
    max_discount_cap: Optional[Decimal]
    usage_limit: Optional[int]
    usage_count: int
    per_user_limit: int
    is_active: bool
    valid_from: datetime
    valid_until: Optional[datetime]

    model_config = {"from_attributes": True}


class CouponValidationRequest(BaseModel):
    code: str
    cart_total: Decimal = Field(..., gt=0)


class CouponValidationResponse(BaseModel):
    valid: bool
    discount_amount: Decimal
    final_total: Decimal
    message: str
