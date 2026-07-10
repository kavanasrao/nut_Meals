"""Business logic for Finance Dashboards."""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import FinanceReportExport, FinanceSummaryCache
from app.schemas.finance import FinanceReportRequest
from app.services.finance_client import FinanceServiceClient


async def get_cached_summary(
    db: AsyncSession, *, period_start: date, period_end: date, granularity: str = "monthly"
) -> FinanceSummaryCache | None:
    query = select(FinanceSummaryCache).where(
        FinanceSummaryCache.period_start == period_start,
        FinanceSummaryCache.period_end == period_end,
        FinanceSummaryCache.granularity == granularity,
    )
    return (await db.execute(query)).scalar_one_or_none()


async def refresh_finance_summary(
    db: AsyncSession,
    *,
    period_start: date,
    period_end: date,
    granularity: str,
    finance_client: FinanceServiceClient,
) -> FinanceSummaryCache:
    """
    Pull fresh figures from the Finance service and upsert the local cache.
    Called both on-demand (cache miss) and periodically by a Celery task.
    """
    summary = await finance_client.get_revenue_expense_summary(period_start, period_end)
    breakdown = await finance_client.get_expense_breakdown(period_start, period_end)

    revenue = summary.get("total_revenue", 0)
    expenses = summary.get("total_expenses", 0)

    cached = await get_cached_summary(
        db, period_start=period_start, period_end=period_end, granularity=granularity
    )
    if cached is None:
        cached = FinanceSummaryCache(
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
        )
        db.add(cached)

    cached.total_revenue = revenue
    cached.total_expenses = expenses
    cached.net_profit = revenue - expenses
    cached.breakdown_json = breakdown
    cached.source_snapshot_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(cached)
    return cached


async def request_finance_report(
    db: AsyncSession, *, data: FinanceReportRequest, requested_by_admin_id: uuid.UUID
) -> FinanceReportExport:
    """
    Create a pending export record and enqueue the Celery task that
    renders and uploads the actual file.
    """
    export = FinanceReportExport(
        requested_by_admin_id=requested_by_admin_id,
        period_start=data.period_start,
        period_end=data.period_end,
        format=data.format,
        status="pending",
    )
    db.add(export)
    await db.flush()
    await db.refresh(export)
    return export


async def get_report_export(db: AsyncSession, export_id: uuid.UUID) -> FinanceReportExport:
    export = await db.get(FinanceReportExport, export_id)
    if export is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report export not found")
    return export
