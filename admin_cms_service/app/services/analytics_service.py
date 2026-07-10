"""Business logic for Analytics / KPI dashboards."""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import KPISnapshot
from app.services.metrics_clients import InventoryServiceClient, PaymentsServiceClient
from app.services.orders_client import OrdersServiceClient


def _safe_div(numerator: float, denominator: float) -> Decimal:
    if not denominator:
        return Decimal("0")
    return Decimal(str(round(numerator / denominator, 4)))


async def compute_daily_kpis(
    *,
    snapshot_date: date,
    orders_client: OrdersServiceClient,
    payments_client: PaymentsServiceClient,
    inventory_client: InventoryServiceClient,
) -> dict:
    """
    Pull raw metrics from Orders, Payments, and Inventory services for a
    single day and derive the KPI figures. Pure computation, no DB access,
    so it's independently unit-testable.
    """
    period_start = snapshot_date
    period_end = snapshot_date

    order_metrics = await orders_client.get_order_metrics(period_start, period_end)
    cohort_metrics = await orders_client.get_customer_cohort_metrics(period_start, period_end)
    funnel_metrics = await payments_client.get_conversion_metrics(period_start, period_end)
    stock_metrics = await inventory_client.get_low_stock_count()

    total_orders = order_metrics.get("total_orders", 0)
    gmv = order_metrics.get("gross_merchandise_value", 0)
    aov = _safe_div(float(gmv), float(total_orders)) if total_orders else Decimal("0")

    total_visitors = funnel_metrics.get("total_visitors", 0)
    conversion_rate = _safe_div(float(total_orders), float(total_visitors))

    new_customers = cohort_metrics.get("new_customers", 0)
    repeat_customers = cohort_metrics.get("repeat_customers", 0)
    churned_customers = cohort_metrics.get("churned_customers", 0)
    total_active = new_customers + repeat_customers

    repeat_rate = _safe_div(float(repeat_customers), float(total_active))
    churn_rate = _safe_div(float(churned_customers), float(total_active))

    return {
        "snapshot_date": snapshot_date,
        "total_orders": total_orders,
        "total_visitors": total_visitors,
        "conversion_rate": conversion_rate,
        "new_customers": new_customers,
        "repeat_customers": repeat_customers,
        "repeat_customer_rate": repeat_rate,
        "churned_customers": churned_customers,
        "churn_rate": churn_rate,
        "gross_merchandise_value": gmv,
        "average_order_value": aov,
        "low_stock_sku_count": stock_metrics.get("low_stock_sku_count", 0),
        "raw_metrics_json": {
            "order_metrics": order_metrics,
            "cohort_metrics": cohort_metrics,
            "funnel_metrics": funnel_metrics,
            "stock_metrics": stock_metrics,
        },
    }


async def upsert_kpi_snapshot(db: AsyncSession, *, kpi_data: dict) -> KPISnapshot:
    query = select(KPISnapshot).where(KPISnapshot.snapshot_date == kpi_data["snapshot_date"])
    existing = (await db.execute(query)).scalar_one_or_none()

    if existing is None:
        existing = KPISnapshot(**kpi_data)
        db.add(existing)
    else:
        for field, value in kpi_data.items():
            setattr(existing, field, value)

    await db.flush()
    await db.refresh(existing)
    return existing


async def get_kpi_trend(db: AsyncSession, *, period_start: date, period_end: date) -> list[KPISnapshot]:
    query = (
        select(KPISnapshot)
        .where(KPISnapshot.snapshot_date >= period_start, KPISnapshot.snapshot_date <= period_end)
        .order_by(KPISnapshot.snapshot_date.asc())
    )
    return list((await db.execute(query)).scalars().all())


async def get_latest_kpi_snapshot(db: AsyncSession) -> KPISnapshot | None:
    query = select(KPISnapshot).order_by(KPISnapshot.snapshot_date.desc()).limit(1)
    return (await db.execute(query)).scalar_one_or_none()


async def get_kpi_summary(db: AsyncSession) -> dict:
    """Latest snapshot plus day-over-day deltas for headline dashboard cards."""
    latest = await get_latest_kpi_snapshot(db)
    if latest is None:
        return {
            "latest": None,
            "conversion_rate_delta": Decimal("0"),
            "repeat_customer_rate_delta": Decimal("0"),
            "churn_rate_delta": Decimal("0"),
        }

    previous_day = latest.snapshot_date - timedelta(days=1)
    query = select(KPISnapshot).where(KPISnapshot.snapshot_date == previous_day)
    previous = (await db.execute(query)).scalar_one_or_none()

    def delta(curr: Decimal, prev: Decimal | None) -> Decimal:
        if prev is None:
            return Decimal("0")
        return Decimal(curr) - Decimal(prev)

    return {
        "latest": latest,
        "conversion_rate_delta": delta(latest.conversion_rate, previous.conversion_rate if previous else None),
        "repeat_customer_rate_delta": delta(
            latest.repeat_customer_rate, previous.repeat_customer_rate if previous else None
        ),
        "churn_rate_delta": delta(latest.churn_rate, previous.churn_rate if previous else None),
    }
