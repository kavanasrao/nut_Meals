"""Integration tests for the Finance Dashboards API, with the upstream
Finance service HTTP client mocked out."""
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.main import app
from app.services.finance_client import get_finance_client


@pytest.fixture
def mock_finance_client():
    mock = AsyncMock()
    mock.get_revenue_expense_summary.return_value = {
        "total_revenue": 100000.00,
        "total_expenses": 62000.00,
    }
    mock.get_expense_breakdown.return_value = {
        "cogs": 40000.00,
        "marketing": 12000.00,
        "logistics": 10000.00,
    }
    app.dependency_overrides[get_finance_client] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_finance_client, None)


@pytest.mark.asyncio
async def test_get_finance_summary_cache_miss_fetches_upstream(
    client, finance_admin_headers, mock_finance_client
):
    resp = await client.get(
        "/api/v1/finance/summary",
        params={"period_start": "2026-06-01", "period_end": "2026-06-30", "granularity": "monthly"},
        headers=finance_admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_revenue"] == "100000.00" or float(body["total_revenue"]) == 100000.00
    assert float(body["net_profit"]) == 38000.00
    mock_finance_client.get_revenue_expense_summary.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_finance_summary_invalid_period_range(client, finance_admin_headers, mock_finance_client):
    resp = await client.get(
        "/api/v1/finance/summary",
        params={"period_start": "2026-06-30", "period_end": "2026-06-01"},
        headers=finance_admin_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_finance_summary_requires_finance_role(client, content_admin_headers, mock_finance_client):
    resp = await client.get(
        "/api/v1/finance/summary",
        params={"period_start": "2026-06-01", "period_end": "2026-06-30"},
        headers=content_admin_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_request_finance_report_enqueues_task(client, finance_admin_headers):
    with patch("app.routes.finance.generate_finance_report_task.delay") as mock_delay:
        resp = await client.post(
            "/api/v1/finance/reports",
            json={"period_start": "2026-06-01", "period_end": "2026-06-30", "format": "csv"},
            headers=finance_admin_headers,
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "pending"
        assert body["format"] == "csv"
        mock_delay.assert_called_once()


@pytest.mark.asyncio
async def test_get_finance_report_not_found(client, finance_admin_headers):
    import uuid

    resp = await client.get(
        f"/api/v1/finance/reports/{uuid.uuid4()}", headers=finance_admin_headers
    )
    assert resp.status_code == 404
