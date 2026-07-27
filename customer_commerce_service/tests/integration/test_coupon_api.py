"""Integration tests for Coupon API."""
from datetime import datetime, timedelta, timezone
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.security import TokenPayload, get_current_user
from app.db.session import get_db

NOW = datetime.now(timezone.utc)

COUPON_PAYLOAD = {
    "code": "TESTOFF20",
    "discount_type": "percent",
    "discount_value": "20",
    "valid_from": (NOW - timedelta(days=1)).isoformat(),
    "valid_until": (NOW + timedelta(days=30)).isoformat(),
    "per_user_limit": 2,
}

_SHARED_USER = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest_asyncio.fixture
async def shared_clients(db_session: AsyncSession):
    """Both admin and customer use the same DB session so coupon is visible cross-role."""

    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: TokenPayload(
        user_id=_SHARED_USER, roles=["admin"], email="admin@test.com"
    )
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    async with client:
        yield client
    app.dependency_overrides.clear()


class TestCouponAPI:
    @pytest.mark.asyncio
    async def test_admin_creates_coupon(self, admin_client):
        resp = await admin_client.post("/api/v1/coupons", json=COUPON_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["code"] == "TESTOFF20"

    @pytest.mark.asyncio
    async def test_customer_cannot_create_coupon(self, client):
        resp = await client.post("/api/v1/coupons", json=COUPON_PAYLOAD)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_validate_valid_coupon(self, shared_clients):
        """Create and validate coupon within the same DB session."""
        resp = await shared_clients.post("/api/v1/coupons", json=COUPON_PAYLOAD)
        assert resp.status_code == 201, resp.text

        # Switch to customer role — same HTTP client, same DB session
        app.dependency_overrides[get_current_user] = lambda: TokenPayload(
            user_id=_SHARED_USER, roles=["customer"], email="cust@test.com"
        )
        resp = await shared_clients.post(
            "/api/v1/coupons/validate",
            json={"code": "TESTOFF20", "cart_total": "1000"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert float(data["discount_amount"]) == 200.0

    @pytest.mark.asyncio
    async def test_validate_nonexistent_coupon(self, client):
        resp = await client.post(
            "/api/v1/coupons/validate",
            json={"code": "NOPE", "cart_total": "500"},
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

    @pytest.mark.asyncio
    async def test_duplicate_coupon_code_rejected(self, admin_client):
        await admin_client.post("/api/v1/coupons", json=COUPON_PAYLOAD)
        resp = await admin_client.post("/api/v1/coupons", json=COUPON_PAYLOAD)
        assert resp.status_code == 409
