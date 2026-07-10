"""Integration tests for gift order endpoints."""
import uuid
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture
def gift_payload():
    return {
        "order_id": str(uuid.uuid4()),
        "gift_message": "Happy Birthday!",
        "recipient_name": "Jane Doe",
        "recipient_email": "jane@example.com",
        "recipient_address_line1": "123 Main St",
        "recipient_city": "Austin",
        "recipient_state": "TX",
        "recipient_postal_code": "78701",
        "recipient_country": "US",
        "gift_wrap_option": "premium",
        "notify_recipient": True,
    }


class TestCreateGiftOrder:
    async def test_create_gift_order_success(self, client, auth_headers, gift_payload):
        with patch("app.services.gift_service.send_gift_notification.delay") as mock_delay:
            resp = await client.post("/api/v1/gift-orders", json=gift_payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["recipient_name"] == "Jane Doe"
        assert body["gift_wrap_option"] == "premium"
        assert body["notification_sent"] is False
        mock_delay.assert_called_once()

    async def test_create_gift_order_requires_auth(self, client, gift_payload):
        resp = await client.post("/api/v1/gift-orders", json=gift_payload)
        assert resp.status_code in (401, 403)

    async def test_create_duplicate_gift_order_conflicts(self, client, auth_headers, gift_payload):
        with patch("app.services.gift_service.send_gift_notification.delay"):
            first = await client.post("/api/v1/gift-orders", json=gift_payload, headers=auth_headers)
            assert first.status_code == 201
            second = await client.post("/api/v1/gift-orders", json=gift_payload, headers=auth_headers)
        assert second.status_code == 409

    async def test_create_gift_order_invalid_email_rejected(self, client, auth_headers, gift_payload):
        gift_payload["recipient_email"] = "not-an-email"
        resp = await client.post("/api/v1/gift-orders", json=gift_payload, headers=auth_headers)
        assert resp.status_code == 422


class TestGetAndUpdateGiftOrder:
    async def test_get_gift_order(self, client, auth_headers, gift_payload):
        with patch("app.services.gift_service.send_gift_notification.delay"):
            created = await client.post("/api/v1/gift-orders", json=gift_payload, headers=auth_headers)
        gift_id = created.json()["id"]

        resp = await client.get(f"/api/v1/gift-orders/{gift_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == gift_id

    async def test_get_gift_order_not_found(self, client, auth_headers):
        resp = await client.get(f"/api/v1/gift-orders/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_update_gift_order(self, client, auth_headers, gift_payload):
        with patch("app.services.gift_service.send_gift_notification.delay"):
            created = await client.post("/api/v1/gift-orders", json=gift_payload, headers=auth_headers)
        gift_id = created.json()["id"]

        resp = await client.patch(
            f"/api/v1/gift-orders/{gift_id}",
            json={"gift_wrap_option": "standard", "notify_recipient": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["gift_wrap_option"] == "standard"

    async def test_update_gift_order_other_customer_forbidden(self, client, auth_headers, gift_payload):
        from app.security.auth import create_access_token

        with patch("app.services.gift_service.send_gift_notification.delay"):
            created = await client.post("/api/v1/gift-orders", json=gift_payload, headers=auth_headers)
        gift_id = created.json()["id"]

        other_token = create_access_token(customer_id=str(uuid.uuid4()), roles=["customer"])
        resp = await client.patch(
            f"/api/v1/gift-orders/{gift_id}",
            json={"gift_wrap_option": "standard"},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403
