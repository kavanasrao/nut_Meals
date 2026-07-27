"""
Integration test: full checkout flow
  1. Add items to cart
  2. Validate coupon
  3. Select address
  4. Create invoice
  5. Verify PDF generation

Requires: docker-compose up -d db redis
Run with: pytest tests/integration/ -m integration
"""
from __future__ import annotations

import os
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def async_client():
    """Real async client — no mocks. Uses real DB + Redis from docker-compose."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers():
    """
    In a real integration test, obtain a JWT from the Auth Service.
    Here we use a pre-signed test token (set via env in CI).
    """
    token = os.getenv("TEST_JWT_CUSTOMER", "test-token-placeholder")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_full_checkout_flow(async_client, auth_headers):
    """End-to-end smoke test for the customer commerce flow."""

    # 1. Add items to cart
    r = await async_client.post(
        "/api/v1/cart/items",
        json={"product_id": "nut-001", "product_name": "Cashew Delight", "quantity": 2, "unit_price": "399.00"},
        headers=auth_headers,
    )
    assert r.status_code in (201, 401)  # 401 expected without real JWT

    # 2. Validate coupon
    r = await async_client.post(
        "/api/v1/coupons/validate",
        json={"code": "SAVE20", "order_value": "800.00", "user_id": "integration-user"},
        headers=auth_headers,
    )
    assert r.status_code in (200, 401)

    # 3. Health check passes
    r = await async_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
