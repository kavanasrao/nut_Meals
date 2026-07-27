"""Pydantic schemas for saved addresses."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.address import AddressType


class AddressBase(BaseModel):
    label: str = Field(default="Home", max_length=50)
    address_type: AddressType = AddressType.OTHER
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., pattern=r"^\+?\d{7,15}$")
    line1: str = Field(..., min_length=1, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    postal_code: str = Field(..., min_length=1, max_length=20)
    landmark: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class AddressCreate(AddressBase):
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: Optional[str] = Field(None, max_length=50)
    address_type: Optional[AddressType] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, pattern=r"^\+?\d{7,15}$")
    line1: Optional[str] = Field(None, min_length=1, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    postal_code: Optional[str] = Field(None, min_length=1, max_length=20)
    landmark: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_default: Optional[bool] = None


class AddressOut(AddressBase):
    id: UUID
    user_id: UUID
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AddressListResponse(BaseModel):
    addresses: list[AddressOut]
    total: int


class AddressSnapshot(BaseModel):
    """Minimal, immutable address payload returned to other services
    (Order Service at checkout, Logistics Service at shipment creation).

    Deliberately excludes `user_id`/`is_default`/timestamps — callers should
    copy this snapshot onto their own order/shipment record rather than
    holding a live reference, since a saved address can later be edited or
    deleted by its owner without that affecting past orders/shipments.
    """

    address_id: UUID
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    country: str
    postal_code: str
    landmark: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}
