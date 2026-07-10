"""Integration tests for the Analytics KPI dashboard API."""
from datetime import date, timedelta

import pytest

from app.models.analytics import KPISnapshot


async def _seed_kpi_snapshot(db_session, snapshot_date: date, **overrides) -> KPISnapshot:
    defaults = dict(
        snapshot_date=snapshot_date,
        total_orders=120,
        total_visitors=3000,
        conversion_rate="0.0400",
        new_customers=40,
        repeat_customers=80,
        repeat_customer_rate="0.6667",
        churned_customers=5,
        churn_rate="0.0417",
        gross_merchandise_value="15000.00",
        average_order_value="125.00",
        low_stock_sku_count=3,
    )
    defaults.update(overrides)
    snapshot = KPISnapshot(**defaults)
    db_session.add(snapshot)
    await db_session.flush()
    return snapshot


@pytest.mark.asyncio
async def test_kpi_summary_no_data_returns_nulls(client, analytics_viewer_headers):
    resp = await client.get("/api/v1/analytics/kpis/summary", headers=analytics_viewer_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest"] is None


@pytest.mark.asyncio
async def test_kpi_summary_with_data_and_delta(client, db_session, analytics_viewer_headers):
    yesterday = date.today() - timedelta(days=1)
    today = date.today()

    await _seed_kpi_snapshot(db_session, yesterday, conversion_rate="0.0300")
    await _seed_kpi_snapshot(db_session, today, conversion_rate="0.0450")

    resp = await client.get("/api/v1/analytics/kpis/summary", headers=analytics_viewer_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["latest"]["snapshot_date"] == today.isoformat()
    assert float(body["conversion_rate_delta"]) == pytest.approx(0.015, rel=1e-3)


@pytest.mark.asyncio
async def test_kpi_trend_default_range(client, db_session, analytics_viewer_headers):
    today = date.today()
    await _seed_kpi_snapshot(db_session, today)

    resp = await client.get("/api/v1/analytics/kpis/trend", headers=analytics_viewer_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["snapshots"]) >= 1


@pytest.mark.asyncio
async def test_kpi_trend_invalid_range_rejected(client, analytics_viewer_headers):
    resp = await client.get(
        "/api/v1/analytics/kpis/trend",
        params={"period_start": "2026-06-30", "period_end": "2026-06-01"},
        headers=analytics_viewer_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_analytics_requires_valid_role(client, support_admin_headers):
    # support_admin is not in the analytics read-role list
    resp = await client.get("/api/v1/analytics/kpis/summary", headers=support_admin_headers)
    assert resp.status_code == 403
