import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.reconciliation import GatewayProvider, ReconciliationRunStatus, SettlementStatus


class SettlementRecordIn(BaseModel):
    """One row from an ingested gateway/bank settlement file."""

    provider_transaction_id: str
    order_reference: str | None = None
    settled_amount_minor: int
    settlement_date: str
    fee_amount_minor: int = 0
    raw_payload: str | None = None


class ReconciliationRunCreate(BaseModel):
    provider: GatewayProvider
    settlement_batch_id: str
    records: list[SettlementRecordIn] = Field(..., min_length=1)
    triggered_by: str = "manual"


class GatewaySettlementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: GatewayProvider
    provider_transaction_id: str
    order_reference: str | None
    settled_amount_minor: int
    settlement_date: str
    fee_amount_minor: int
    status: SettlementStatus


class ReconciliationExceptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    settlement_id: uuid.UUID
    reason: str
    expected_amount_minor: int | None
    actual_amount_minor: int | None
    resolved: bool
    resolved_by: str | None
    resolution_notes: str | None
    created_at: datetime


class ReconciliationExceptionResolve(BaseModel):
    resolution_notes: str = Field(..., min_length=1, max_length=1000)


class ReconciliationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: GatewayProvider
    settlement_batch_id: str
    status: ReconciliationRunStatus
    total_records: int
    matched_records: int
    exception_records: int
    triggered_by: str
    error_message: str | None
    created_at: datetime
