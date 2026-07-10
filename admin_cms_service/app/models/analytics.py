"""
ORM models for Analytics: KPI snapshots aggregated from Orders, Payments,
and Inventory services by scheduled Celery tasks.
"""
from datetime import date
from typing import Optional

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class KPISnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A point-in-time rollup of key business metrics for a given day.
    One row per calendar day; recomputed/upserted by the nightly
    analytics aggregation task (see app/tasks/analytics_tasks.py).
    """

    __tablename__ = "kpi_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_date", name="uq_kpi_snapshot_date"),)

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    total_orders: Mapped[int] = mapped_column(default=0, nullable=False)
    total_visitors: Mapped[int] = mapped_column(default=0, nullable=False)
    conversion_rate: Mapped[Numeric] = mapped_column(Numeric(6, 4), default=0, nullable=False)

    new_customers: Mapped[int] = mapped_column(default=0, nullable=False)
    repeat_customers: Mapped[int] = mapped_column(default=0, nullable=False)
    repeat_customer_rate: Mapped[Numeric] = mapped_column(Numeric(6, 4), default=0, nullable=False)

    churned_customers: Mapped[int] = mapped_column(default=0, nullable=False)
    churn_rate: Mapped[Numeric] = mapped_column(Numeric(6, 4), default=0, nullable=False)

    gross_merchandise_value: Mapped[Numeric] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    average_order_value: Mapped[Numeric] = mapped_column(Numeric(10, 2), default=0, nullable=False)

    low_stock_sku_count: Mapped[int] = mapped_column(default=0, nullable=False)

    raw_metrics_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
