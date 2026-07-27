"""
Pydantic schemas for Amazon Multi-Channel Fulfillment (MCF).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ShippingSpeed(str, Enum):
    STANDARD = "Standard"
    EXPEDITED = "Expedited"
    PRIORITY = "Priority"


class FulfillmentStatus(str, Enum):
    RECEIVED = "Received"
    PLANNING = "Planning"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    CANCELLED = "Cancelled"
    COMPLETE = "Complete"


class Address(BaseModel):
    name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country_code: str = "IN"
    phone: Optional[str] = None


class OrderItem(BaseModel):
    seller_sku: str
    quantity: int = Field(..., gt=0)


class FulfillmentOrderCreate(BaseModel):
    seller_order_id: str
    displayable_order_id: str
    displayable_order_date: datetime

    shipping_speed: ShippingSpeed = ShippingSpeed.STANDARD

    destination_address: Address

    items: list[OrderItem]


class FulfillmentOrderResponse(BaseModel):
    fulfillment_order_id: str
    seller_order_id: str
    status: FulfillmentStatus
    shipping_speed: ShippingSpeed

    tracking_number: Optional[str] = None
    carrier: Optional[str] = None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class InventoryItem(BaseModel):
    seller_sku: str
    fulfillable_quantity: int


class TrackingResponse(BaseModel):
    tracking_number: str
    carrier: str
    tracking_url: Optional[str] = None
    status: FulfillmentStatus