import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.journal import JournalEntryStatus, JournalSourceType


class JournalLineIn(BaseModel):
    account_id: uuid.UUID
    debit_amount_minor: int = Field(0, ge=0)
    credit_amount_minor: int = Field(0, ge=0)
    memo: str | None = None

    @model_validator(mode="after")
    def one_sided(self) -> "JournalLineIn":
        if (self.debit_amount_minor > 0) == (self.credit_amount_minor > 0):
            raise ValueError("Each line must have exactly one of debit_amount_minor / credit_amount_minor > 0")
        return self


class JournalEntryCreate(BaseModel):
    entry_date: str = Field(..., description="ISO date YYYY-MM-DD", examples=["2026-07-10"])
    description: str = Field(..., min_length=1, max_length=1000)
    source_type: JournalSourceType
    source_reference: str = Field(..., min_length=1, max_length=100)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    lines: list[JournalLineIn] = Field(..., min_length=2)

    @model_validator(mode="after")
    def balanced(self) -> "JournalEntryCreate":
        total_debit = sum(line.debit_amount_minor for line in self.lines)
        total_credit = sum(line.credit_amount_minor for line in self.lines)
        if total_debit != total_credit:
            raise ValueError(f"Unbalanced entry: debits={total_debit} credits={total_credit}")
        if total_debit == 0:
            raise ValueError("Journal entry must have a non-zero amount")
        return self


class JournalLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    line_number: int
    debit_amount_minor: int
    credit_amount_minor: int
    memo: str | None


class JournalEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_number: str
    entry_date: str
    description: str
    status: JournalEntryStatus
    source_type: JournalSourceType
    source_reference: str
    currency: str
    created_by: str
    posted_by: str | None
    reversal_of_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    lines: list[JournalLineOut]


class JournalEntryReverseRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)
