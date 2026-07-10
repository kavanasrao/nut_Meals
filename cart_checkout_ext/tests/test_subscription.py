"""Integration tests for subscription lifecycle endpoints."""
import uuid

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def subscription_payload():
    return {
        "plan_id": "weekly-family-plan",
        "plan_snapshot": {"meals_per_week": 5, "servings": 4},
        "frequency": "weekly",
        "price_amount": 79.99,
        "currency": "USD",
        "payment_method_token": "pm_tok_test_123",
        "shipping_address_id": str(uuid.uuid4()),
    }


class TestCreateSubscription:
    async def test_create_subscription_success(self, client, auth_headers, subscription_payload):
        resp = await client.post("/api/v1/subscriptions", json=subscription_payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "active"
        assert body["frequency"] == "weekly"
        assert body["failed_renewal_attempts"] == 0

    async def test_create_subscription_rejects_zero_price(self, client, auth_headers, subscription_payload):
        subscription_payload["price_amount"] = 0
        resp = await client.post("/api/v1/subscriptions", json=subscription_payload, headers=auth_headers)
        assert resp.status_code == 422

    async def test_list_subscriptions(self, client, auth_headers, subscription_payload):
        await client.post("/api/v1/subscriptions", json=subscription_payload, headers=auth_headers)
        resp = await client.get("/api/v1/subscriptions", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestSubscriptionLifecycle:
    async def _create(self, client, auth_headers, payload):
        resp = await client.post("/api/v1/subscriptions", json=payload, headers=auth_headers)
        return resp.json()["id"]

    async def test_pause_and_resume(self, client, auth_headers, subscription_payload):
        sub_id = await self._create(client, auth_headers, subscription_payload)

        pause_resp = await client.post(
            f"/api/v1/subscriptions/{sub_id}/pause", json={"reason": "traveling"}, headers=auth_headers
        )
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "paused"

        resume_resp = await client.post(f"/api/v1/subscriptions/{sub_id}/resume", headers=auth_headers)
        assert resume_resp.status_code == 200
        assert resume_resp.json()["status"] == "active"

    async def test_cannot_pause_twice(self, client, auth_headers, subscription_payload):
        sub_id = await self._create(client, auth_headers, subscription_payload)
        await client.post(f"/api/v1/subscriptions/{sub_id}/pause", json={}, headers=auth_headers)
        second_pause = await client.post(f"/api/v1/subscriptions/{sub_id}/pause", json={}, headers=auth_headers)
        assert second_pause.status_code == 400

    async def test_cancel_subscription(self, client, auth_headers, subscription_payload):
        sub_id = await self._create(client, auth_headers, subscription_payload)
        resp = await client.post(
            f"/api/v1/subscriptions/{sub_id}/cancel",
            json={"reason": "no longer needed"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_cannot_cancel_twice(self, client, auth_headers, subscription_payload):
        sub_id = await self._create(client, auth_headers, subscription_payload)
        await client.post(f"/api/v1/subscriptions/{sub_id}/cancel", json={}, headers=auth_headers)
        second_cancel = await client.post(f"/api/v1/subscriptions/{sub_id}/cancel", json={}, headers=auth_headers)
        assert second_cancel.status_code == 400

    async def test_subscription_not_found(self, client, auth_headers):
        resp = await client.get(f"/api/v1/subscriptions/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
