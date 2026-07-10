"""Pydantic schemas for the Analytics API."""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class KPISnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: date
    total_orders: int
    total_visitors: int
    conversion_rate: Decimal
    new_customers: int
    repeat_customers: int
    repeat_customer_rate: Decimal
    churned_customers: int
    churn_rate: Decimal
    gross_merchandise_value: Decimal
    average_order_value: Decimal
    low_stock_sku_count: int


class KPITrendResponse(BaseModel):
    """Time-series of KPI snapshots for dashboard charting."""

    snapshots: list[KPISnapshotResponse]
    period_start: date
    period_end: date


class KPISummaryResponse(BaseModel):
    """Latest single-day snapshot plus period-over-period deltas, for headline cards."""

    latest: Optional[KPISnapshotResponse]
    conversion_rate_delta: Decimal
    repeat_customer_rate_delta: Decimal
    churn_rate_delta: Decimal
