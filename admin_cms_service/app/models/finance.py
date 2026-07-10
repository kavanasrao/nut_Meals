"""
ORM models supporting Finance Dashboards.

The Admin CMS Service does not own financial ledgers -- those live in
the Finance service. This service caches periodic aggregates (for fast
dashboard rendering) and tracks generated/exported reports.
"""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class FinanceSummaryCache(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Cached revenue/expense/P&L rollup for a given period, refreshed by a
    Celery beat task that pulls from the Finance service. Serving reads
    from this table avoids hammering Finance service on every dashboard
    page load.
    """

    __tablename__ = "finance_summary_cache"
    __table_args__ = (
        UniqueConstraint("period_start", "period_end", "granularity", name="uq_finance_period"),
    )

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    granularity: Mapped[str] = mapped_column(String(20), nullable=False)  # daily|weekly|monthly

    total_revenue: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_expenses: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    net_profit: Mapped[Numeric] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    breakdown_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    source_snapshot_at: Mapped[datetime] = mapped_column(nullable=False)


class FinanceReportExport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A generated, downloadable finance report (CSV/PDF/XLSX)."""

    __tablename__ = "finance_report_exports"

    requested_by_admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)  # csv|pdf|xlsx
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
