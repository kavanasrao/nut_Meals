"""
Celery tasks for Analytics: nightly aggregation of KPIs from Orders,
Payments, and Inventory services into local KPISnapshot rows.
"""
import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import select

from app.models.analytics import KPISnapshot
from app.services.analytics_service import compute_daily_kpis
from app.services.metrics_clients import InventoryServiceClient, PaymentsServiceClient
from app.services.orders_client import OrdersServiceClient
from app.tasks.celery_app import celery_app
from app.tasks.db import get_sync_db

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.analytics_tasks.aggregate_daily_kpis_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def aggregate_daily_kpis_task(self, target_date_iso: str | None = None) -> str:
    """
    Compute and persist the KPI snapshot for a given day (defaults to
    yesterday, since "today" is still in progress). Idempotent: re-running
    for the same date upserts the existing row.
    """
    target_date = date.fromisoformat(target_date_iso) if target_date_iso else date.today() - timedelta(days=1)

    try:
        kpi_data = asyncio.run(_fetch_kpi_data(target_date))
    except Exception as exc:
        logger.exception("Failed to fetch KPI data for %s", target_date)
        raise self.retry(exc=exc)

    with get_sync_db() as db:
        existing = db.execute(
            select(KPISnapshot).where(KPISnapshot.snapshot_date == target_date)
        ).scalar_one_or_none()

        if existing is None:
            db.add(KPISnapshot(**kpi_data))
        else:
            for field, value in kpi_data.items():
                setattr(existing, field, value)

    logger.info("KPI snapshot upserted for %s", target_date)
    return f"kpi_snapshot:{target_date.isoformat()}"


async def _fetch_kpi_data(target_date: date) -> dict:
    return await compute_daily_kpis(
        snapshot_date=target_date,
        orders_client=OrdersServiceClient(),
        payments_client=PaymentsServiceClient(),
        inventory_client=InventoryServiceClient(),
    )


@celery_app.task(name="app.tasks.analytics_tasks.backfill_kpis_task")
def backfill_kpis_task(start_date_iso: str, end_date_iso: str) -> list[str]:
    """Admin-triggered backfill of KPI snapshots over a date range (inclusive)."""
    start = date.fromisoformat(start_date_iso)
    end = date.fromisoformat(end_date_iso)
    results = []
    current = start
    while current <= end:
        results.append(aggregate_daily_kpis_task(current.isoformat()))
        current += timedelta(days=1)
    return results
