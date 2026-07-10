"""Pydantic schemas for one-click login checkout."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SavedAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    line1: str
    line2: str | None
    city: str
    state: str
    postal_code: str
    country: str
    is_default: bool


class SavedPaymentMethodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand: str | None
    last4: str | None
    exp_month: int | None
    exp_year: int | None
    is_default: bool


class OneClickTokenIssueRequest(BaseModel):
    """Issued only after the caller has already authenticated a normal
    session; this token is a short-lived convenience credential for the
    checkout flow, not a replacement for primary login."""
    pass


class OneClickTokenResponse(BaseModel):
    token: str
    expires_at: datetime


class OneClickCheckoutRequest(BaseModel):
    token: str
    saved_address_id: uuid.UUID
    saved_payment_method_id: uuid.UUID
    order_id: uuid.UUID


class OneClickCheckoutResponse(BaseModel):
    order_id: uuid.UUID
    status: str
    address: SavedAddressResponse
    payment_method: SavedPaymentMethodResponse
