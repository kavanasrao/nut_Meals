"""Saved address schemas."""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AddressCreate(BaseModel):
    label: str = Field(..., max_length=64)
    full_name: str = Field(..., max_length=128)
    phone: str = Field(..., max_length=20, pattern=r"^\+?[0-9]{7,15}$")
    line1: str = Field(..., max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=10, pattern=r"^[1-9][0-9]{5}$")
    country: str = Field("India", max_length=64)
    is_default: bool = False
    gstin: Optional[str] = Field(None, max_length=15, pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


class AddressUpdate(AddressCreate):
    pass


class AddressResponse(BaseModel):
    id: UUID
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

    model_config = {"from_attributes": True}
