"""Pydantic v2 schemas (request / response) for all domains."""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# CART
# ══════════════════════════════════════════════════════════════════════════════

class CartItemCreate(BaseModel):
    product_id: str
    product_name: str
    quantity: int = Field(ge=1, le=100)
    unit_price: Decimal = Field(ge=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=100)


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal = Field(default=Decimal("0"))

    @classmethod
    def from_orm_item(cls, item) -> "CartItemOut":
        return cls(
            id=item.id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.unit_price * item.quantity,
        )


class CartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    items: List[CartItemOut]
    subtotal: Decimal


# ══════════════════════════════════════════════════════════════════════════════
# WISHLIST
# ══════════════════════════════════════════════════════════════════════════════

class WishlistItemCreate(BaseModel):
    product_id: str
    product_name: str
    unit_price: Decimal = Field(ge=0)
    product_image_url: Optional[str] = None


class WishlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    product_id: str
    product_name: str
    unit_price: Decimal
    product_image_url: Optional[str]


# ══════════════════════════════════════════════════════════════════════════════
# COUPON ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class CouponCreate(BaseModel):
    code: str = Field(min_length=3, max_length=50)
    description: Optional[str] = None
    discount_type: str  # percent | fixed
    discount_value: Decimal = Field(gt=0)
    min_order_value: Decimal = Field(ge=0, default=Decimal("0"))
    max_discount_cap: Optional[Decimal] = None
    max_uses: Optional[int] = Field(default=None, ge=1)
    max_uses_per_user: int = Field(default=1, ge=1)
    valid_from: Optional[str] = None   # ISO-8601 datetime string
    valid_until: Optional[str] = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.upper()

    @field_validator("discount_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("percent", "fixed"):
            raise ValueError("discount_type must be 'percent' or 'fixed'")
        return v


class CouponUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None
    max_uses: Optional[int] = Field(default=None, ge=1)
    valid_until: Optional[str] = None


class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    description: Optional[str]
    discount_type: str
    discount_value: Decimal
    min_order_value: Decimal
    max_uses: Optional[int]
    times_used: int
    is_active: bool
    valid_from: Optional[str]
    valid_until: Optional[str]


class CouponValidateRequest(BaseModel):
    code: str
    order_value: Decimal = Field(gt=0)
    user_id: str


class CouponValidateResponse(BaseModel):
    valid: bool
    discount_amount: Decimal = Decimal("0")
    final_order_value: Decimal
    message: str


# ══════════════════════════════════════════════════════════════════════════════
# ADDRESS
# ══════════════════════════════════════════════════════════════════════════════

class AddressCreate(BaseModel):
    label: str = "Home"
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    line1: str = Field(min_length=5, max_length=255)
    line2: Optional[str] = None
    city: str
    state: str
    pincode: str = Field(min_length=6, max_length=10)
    country: str = "India"
    is_default: bool = False
    gstin: Optional[str] = Field(default=None, max_length=15)


class AddressUpdate(BaseModel):
    label: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_default: Optional[bool] = None
    gstin: Optional[str] = None


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    label: str
    full_name: str
    phone: str
    line1: str
    line2: Optional[str]
    city: str
    state: str
    pincode: str
    country: str
    is_default: bool
    gstin: Optional[str]


# ══════════════════════════════════════════════════════════════════════════════
# INVOICE
# ══════════════════════════════════════════════════════════════════════════════

class InvoiceItemIn(BaseModel):
    product_id: str
    product_name: str
    hsn_code: str = "21069099"
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(ge=0)
    gst_rate: Decimal = Field(ge=0)


class InvoiceCreate(BaseModel):
    order_id: str
    user_id: str
    items: List[InvoiceItemIn]
    discount_amount: Decimal = Decimal("0")
    buyer_name: str
    buyer_address: str
    buyer_gstin: Optional[str] = None


class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: str
    product_name: str
    hsn_code: str
    quantity: int
    unit_price: Decimal
    gst_rate: Decimal
    line_total: Decimal


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    invoice_number: str
    order_id: str
    user_id: str
    subtotal: Decimal
    discount_amount: Decimal
    taxable_amount: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    total_amount: Decimal
    buyer_name: str
    buyer_address: str
    buyer_gstin: Optional[str]
    pdf_url: Optional[str]
    status: str
    items: List[InvoiceItemOut]
