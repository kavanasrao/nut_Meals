"""Pydantic schemas for the Finance Dashboards API."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class FinanceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period_start: date
    period_end: date
    granularity: str
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    breakdown_json: Optional[dict] = None
    source_snapshot_at: datetime


class FinanceReportRequest(BaseModel):
    period_start: date
    period_end: date
    format: str = Field(default="csv", pattern="^(csv|pdf|xlsx)$")


class FinanceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    period_start: date
    period_end: date
    format: str
    status: str
    file_url: Optional[str]
    error_message: Optional[str]
    created_at: datetime
