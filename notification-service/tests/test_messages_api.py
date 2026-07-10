import pytest


@pytest.mark.asyncio
async def test_list_messages_empty(client, auth_headers):
    resp = await client.get("/api/v1/messages", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_create_and_get_message(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/messages",
        headers=auth_headers,
        json={
            "event_type": "delivery.updated",
            "channel": "push",
            "recipient": "device-token-abc",
            "body": "Your delivery is on the way",
            "idempotency_key": "msg-key-1",
        },
    )
    assert create_resp.status_code == 202
    message_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/messages/{message_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == message_id


@pytest.mark.asyncio
async def test_get_nonexistent_message_404(client, auth_headers):
    resp = await client.get("/api/v1/messages/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_filter_messages_by_channel(client, auth_headers):
    await client.post(
        "/api/v1/messages",
        headers=auth_headers,
        json={
            "event_type": "order.status_changed",
            "channel": "webhook",
            "recipient": "https://partner.example.com/hook",
            "body": "order update",
            "idempotency_key": "msg-key-2",
        },
    )
    resp = await client.get("/api/v1/messages?channel=webhook", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["channel"] == "webhook"
