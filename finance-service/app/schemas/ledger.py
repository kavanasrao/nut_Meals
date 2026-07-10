import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ledger import AccountType


class LedgerAccountCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=20, examples=["1200"])
    name: str = Field(..., min_length=1, max_length=120)
    account_type: AccountType
    description: str | None = None
    parent_id: uuid.UUID | None = None


class LedgerAccountUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class LedgerAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    account_type: AccountType
    description: str | None
    is_active: bool
    is_system_account: bool
    parent_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class LedgerAccountBalance(BaseModel):
    account: LedgerAccountOut
    debit_total_minor: int
    credit_total_minor: int
    balance_minor: int  # signed, per the account's normal balance
