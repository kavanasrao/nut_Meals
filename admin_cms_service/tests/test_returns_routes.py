"""Integration tests for the Returns Management API."""
import uuid
from unittest.mock import AsyncMock

import pytest

from app.main import app
from app.models.returns import ReturnRequest
from app.services.logistics_client import get_logistics_client


async def _seed_return_request(db_session) -> ReturnRequest:
    ret = ReturnRequest(
        order_id=uuid.uuid4(),
        customer_id=uuid.uuid4(),
        reason="Damaged in transit",
    )
    db_session.add(ret)
    await db_session.flush()
    await db_session.refresh(ret)
    return ret


@pytest.mark.asyncio
async def test_list_returns_empty(client, support_admin_headers):
    resp = await client.get("/api/v1/returns", headers=support_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_approve_return_tier_a_no_restock(client, db_session, support_admin_headers):
    ret = await _seed_return_request(db_session)

    resp = await client.post(
        f"/api/v1/returns/{ret.id}/approve",
        json={"tier": "A", "refund_amount": "19.99", "restock_required": False},
        headers=support_admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["tier"] == "A"
    assert body["refund_amount"] == "19.99"


@pytest.mark.asyncio
async def test_approve_return_with_restock_triggers_logistics(client, db_session, support_admin_headers):
    ret = await _seed_return_request(db_session)

    mock_logistics = AsyncMock()
    mock_logistics.schedule_return_pickup.return_value = {"reference": "PICKUP-123"}

    app.dependency_overrides[get_logistics_client] = lambda: mock_logistics
    try:
        resp = await client.post(
            f"/api/v1/returns/{ret.id}/approve",
            json={"tier": "C", "refund_amount": "45.00", "restock_required": True},
            headers=support_admin_headers,
        )
    finally:
        app.dependency_overrides.pop(get_logistics_client, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "C"
    assert body["logistics_reference"] == "PICKUP-123"
    mock_logistics.schedule_return_pickup.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_return(client, db_session, support_admin_headers):
    ret = await _seed_return_request(db_session)

    resp = await client.post(
        f"/api/v1/returns/{ret.id}/reject",
        json={"tier": "A", "resolution_notes": "Outside return window"},
        headers=support_admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_cannot_redecide_already_approved_return(client, db_session, support_admin_headers):
    ret = await _seed_return_request(db_session)

    first = await client.post(
        f"/api/v1/returns/{ret.id}/approve",
        json={"tier": "A", "restock_required": False},
        headers=support_admin_headers,
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/returns/{ret.id}/reject",
        json={"tier": "A"},
        headers=support_admin_headers,
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_returns_require_decision_role(client, db_session, analytics_viewer_headers):
    ret = await _seed_return_request(db_session)

    resp = await client.post(
        f"/api/v1/returns/{ret.id}/approve",
        json={"tier": "A"},
        headers=analytics_viewer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_nonexistent_return_404(client, support_admin_headers):
    resp = await client.get(
        f"/api/v1/returns/{uuid.uuid4()}", headers=support_admin_headers
    )
    assert resp.status_code == 404
