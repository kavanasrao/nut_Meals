import pytest


@pytest.mark.asyncio
async def test_trigger_notification_requires_auth(client):
    resp = await client.post("/api/v1/notifications/trigger", json={
        "event_type": "order.status_changed",
        "recipient": "user@example.com",
        "channel": "email",
        "body": "Your order shipped!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_trigger_notification_success(client, auth_headers):
    resp = await client.post(
        "/api/v1/notifications/trigger",
        headers=auth_headers,
        json={
            "event_type": "order.status_changed",
            "recipient": "user@example.com",
            "channel": "email",
            "subject": "Order update",
            "body": "Your order shipped!",
            "correlation_id": "order-123",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["channel"] == "email"
    assert data["correlation_id"] == "order-123"


@pytest.mark.asyncio
async def test_trigger_notification_idempotent(client, auth_headers):
    payload = {
        "event_type": "payment.confirmed",
        "recipient": "+15551234567",
        "channel": "sms",
        "body": "Payment received",
        "idempotency_key": "fixed-key-1",
    }
    first = await client.post("/api/v1/notifications/trigger", headers=auth_headers, json=payload)
    second = await client.post("/api/v1/notifications/trigger", headers=auth_headers, json=payload)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_support_role_cannot_trigger(client):
    from app.core.security import create_access_token

    token = create_access_token(subject="support-1", roles=["support"])
    resp = await client.post(
        "/api/v1/notifications/trigger",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_type": "x", "recipient": "a@b.com", "channel": "email", "body": "hi"},
    )
    assert resp.status_code == 403
