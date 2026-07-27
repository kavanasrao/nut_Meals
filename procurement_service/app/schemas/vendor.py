import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import LedgerEntrySource, LedgerEntryType, VendorStatus


class VendorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    payment_terms_days: int = Field(default=30, ge=0, le=365)


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    address: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    payment_terms_days: Optional[int] = Field(None, ge=0, le=365)
    status: Optional[VendorStatus] = None


class VendorRead(VendorBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: VendorStatus
    created_at: datetime
    updated_at: datetime


class VendorListResponse(BaseModel):
    items: list[VendorRead]
    total: int
    page: int
    page_size: int


class VendorLedgerEntryCreate(BaseModel):
    entry_type: LedgerEntryType
    source: LedgerEntrySource
    reference_id: Optional[uuid.UUID] = None
    amount: Decimal = Field(..., gt=0, description="Always positive; sign implied by entry_type")
    description: Optional[str] = None


class VendorLedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vendor_id: uuid.UUID
    entry_type: LedgerEntryType
    source: LedgerEntrySource
    reference_id: Optional[uuid.UUID]
    amount: Decimal
    balance_after: Decimal
    description: Optional[str]
    finance_service_synced: bool
    finance_service_ref: Optional[str]
    created_at: datetime


class VendorLedgerResponse(BaseModel):
    vendor_id: uuid.UUID
    current_balance: Decimal
    entries: list[VendorLedgerEntryRead]
