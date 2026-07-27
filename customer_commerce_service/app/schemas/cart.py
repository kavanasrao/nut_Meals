"""Cart + CartItem request/response schemas."""
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CartItemCreate(BaseModel):
    product_id: UUID
    product_name: str = Field(..., max_length=255)
    unit_price: Decimal = Field(..., gt=0, decimal_places=2)
    quantity: int = Field(1, ge=1, le=100)
    image_url: Optional[str] = None


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=100)


class CartItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    unit_price: Decimal
    quantity: int
    image_url: Optional[str]
    line_total: Decimal

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_total(cls, item) -> "CartItemResponse":
        return cls(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            image_url=item.image_url,
            line_total=item.unit_price * item.quantity,
        )


class CartResponse(BaseModel):
    id: UUID
    user_id: UUID
    items: List[CartItemResponse]
    coupon_code: Optional[str]
    subtotal: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


class ApplyCouponRequest(BaseModel):
    coupon_code: str = Field(..., min_length=1, max_length=64)
