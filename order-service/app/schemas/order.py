"""Pydantic request/response schemas for the Order Service."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.order import OrderStatus


# ---------------------------------------------------------------------------
# Sub-schemas
# ---------------------------------------------------------------------------

class OrderItemIn(BaseModel):
    meal_id: str = Field(..., min_length=1, max_length=255)
    meal_name: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(..., ge=1, le=100)
    unit_price: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)


class OrderItemOut(BaseModel):
    id: UUID
    meal_id: str
    meal_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = {"from_attributes": True}


class DeliveryAddress(BaseModel):
    street: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    pincode: str = Field(..., pattern=r"^\d{6}$")
    landmark: Optional[str] = Field(None, max_length=300)


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class OrderCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=255)
    items: list[OrderItemIn] = Field(..., min_length=1)
    delivery_type: str = Field(default="home_delivery", pattern=r"^(home_delivery|pickup)$")
    delivery_address: Optional[DeliveryAddress] = None
    special_instructions: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def validate_home_delivery_has_address(self) -> "OrderCreate":
        if self.delivery_type == "home_delivery" and self.delivery_address is None:
            raise ValueError("delivery_address is required for home_delivery")
        return self


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class OrderOut(BaseModel):
    id: UUID
    user_id: str
    status: OrderStatus
    delivery_type: str
    delivery_address: Optional[dict[str, Any]] = None
    special_instructions: Optional[str] = None
    subtotal: Decimal
    tax_amount: Decimal
    delivery_charge: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    items: list[OrderItemOut]
    created_at: str  # ISO-8601 string for JSON transport
    updated_at: str

    model_config = {"from_attributes": True}
