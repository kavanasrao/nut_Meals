"""Unit tests for app.services.analytics_service.compute_daily_kpis."""
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.services.analytics_service import compute_daily_kpis, _safe_div


def test_safe_div_handles_zero_denominator():
    assert _safe_div(10, 0) == Decimal("0")


def test_safe_div_normal_case():
    assert _safe_div(1, 4) == Decimal("0.25")


@pytest.mark.asyncio
async def test_compute_daily_kpis_derives_rates_correctly():
    orders_client = AsyncMock()
    orders_client.get_order_metrics.return_value = {
        "total_orders": 50,
        "gross_merchandise_value": 5000,
    }
    orders_client.get_customer_cohort_metrics.return_value = {
        "new_customers": 20,
        "repeat_customers": 30,
        "churned_customers": 5,
    }

    payments_client = AsyncMock()
    payments_client.get_conversion_metrics.return_value = {"total_visitors": 1000}

    inventory_client = AsyncMock()
    inventory_client.get_low_stock_count.return_value = {"low_stock_sku_count": 7}

    result = await compute_daily_kpis(
        snapshot_date=date(2026, 6, 15),
        orders_client=orders_client,
        payments_client=payments_client,
        inventory_client=inventory_client,
    )

    assert result["total_orders"] == 50
    assert result["conversion_rate"] == Decimal("0.05")  # 50/1000
    assert result["average_order_value"] == Decimal("100")  # 5000/50
    assert result["repeat_customer_rate"] == Decimal("0.6")  # 30/50
    assert result["churn_rate"] == Decimal("0.1")  # 5/50
    assert result["low_stock_sku_count"] == 7


@pytest.mark.asyncio
async def test_compute_daily_kpis_handles_zero_orders():
    orders_client = AsyncMock()
    orders_client.get_order_metrics.return_value = {"total_orders": 0, "gross_merchandise_value": 0}
    orders_client.get_customer_cohort_metrics.return_value = {
        "new_customers": 0,
        "repeat_customers": 0,
        "churned_customers": 0,
    }
    payments_client = AsyncMock()
    payments_client.get_conversion_metrics.return_value = {"total_visitors": 0}
    inventory_client = AsyncMock()
    inventory_client.get_low_stock_count.return_value = {"low_stock_sku_count": 0}

    result = await compute_daily_kpis(
        snapshot_date=date(2026, 6, 15),
        orders_client=orders_client,
        payments_client=payments_client,
        inventory_client=inventory_client,
    )

    assert result["conversion_rate"] == Decimal("0")
    assert result["average_order_value"] == Decimal("0")
    assert result["repeat_customer_rate"] == Decimal("0")
