"""Pydantic request/response schemas for gift order endpoints."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.gift import GiftWrapOption


class GiftOrderCreate(BaseModel):
    order_id: uuid.UUID
    gift_message: str | None = Field(default=None, max_length=1000)
    recipient_name: str = Field(..., max_length=255)
    recipient_email: EmailStr | None = None
    recipient_phone: str | None = Field(default=None, max_length=32)
    recipient_address_line1: str = Field(..., max_length=255)
    recipient_address_line2: str | None = Field(default=None, max_length=255)
    recipient_city: str = Field(..., max_length=120)
    recipient_state: str = Field(..., max_length=120)
    recipient_postal_code: str = Field(..., max_length=20)
    recipient_country: str = Field(default="US", min_length=2, max_length=2)
    gift_wrap_option: GiftWrapOption = GiftWrapOption.NONE
    scheduled_delivery_date: datetime | None = None
    notify_recipient: bool = False


class GiftOrderUpdate(BaseModel):
    gift_message: str | None = Field(default=None, max_length=1000)
    gift_wrap_option: GiftWrapOption | None = None
    scheduled_delivery_date: datetime | None = None
    notify_recipient: bool | None = None


class GiftOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    customer_id: uuid.UUID
    is_gift: bool
    gift_message: str | None
    recipient_name: str
    recipient_email: str | None
    recipient_phone: str | None
    recipient_address_line1: str
    recipient_address_line2: str | None
    recipient_city: str
    recipient_state: str
    recipient_postal_code: str
    recipient_country: str
    gift_wrap_option: GiftWrapOption
    scheduled_delivery_date: datetime | None
    notify_recipient: bool
    notification_sent: bool
    created_at: datetime
    updated_at: datetime
