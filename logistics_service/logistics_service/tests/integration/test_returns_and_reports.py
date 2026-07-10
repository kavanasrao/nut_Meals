"""Integration tests for the returns and reports routes, and tracking force-refresh."""
from unittest.mock import AsyncMock

import uuid

import fakeredis.aioredis
import jwt
import pytest

from app.config import get_settings
from app.models.shipment import Shipment, ShipmentStatus, ShipmentType

settings = get_settings()


def _auth_headers(roles: list[str]) -> dict:
    token = jwt.encode({"sub": "test-user", "roles": roles}, key="", algorithm="none")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def patch_jwt_no_verify(monkeypatch):
    monkeypatch.setattr(settings, "jwt_public_key", "")


@pytest.mark.asyncio
async def test_create_return_success(client, db_session, seeded_carriers, monkeypatch):
    from app.services import returns as returns_module
    from tests.conftest import FakeAdapter

    adapter = FakeAdapter("delhivery", awb="DL-ORIG-1")
    monkeypatch.setattr(returns_module, "get_adapter", lambda code: adapter)

    original = Shipment(
        id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        order_id=uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        carrier_id=seeded_carriers["delhivery"].id,
        carrier_awb="DL-ORIG-1",
        shipment_type=ShipmentType.FORWARD,
        status=ShipmentStatus.DELIVERED,
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=1.0,
        cod_amount=0,
        meta={},
    )
    db_session.add(original)
    await db_session.commit()

    resp = await client.post(
        "/v1/returns",
        json={
            "original_shipment_id": str(original.id),
            "reason": "damaged",
            "pickup_pincode": "110001",
            "weight_kg": 1.0,
        },
        headers=_auth_headers(["logistics_ops"]),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["shipment_type"] == "reverse"


@pytest.mark.asyncio
async def test_create_return_shipment_not_found(client):
    resp = await client.post(
        "/v1/returns",
        json={
            "original_shipment_id": "00000000-0000-0000-0000-000000000000",
            "reason": "damaged",
            "pickup_pincode": "110001",
            "weight_kg": 1.0,
        },
        headers=_auth_headers(["logistics_ops"]),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_audit_log_csv_export(client):
    resp = await client.get(
        "/v1/reports/audit-log.csv",
        params={"start": "2026-01-01T00:00:00Z", "end": "2026-12-31T00:00:00Z"},
        headers=_auth_headers(["compliance_officer"]),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "id,entity_type,entity_id" in resp.text


@pytest.mark.asyncio
async def test_audit_log_csv_export_forbidden_without_role(client):
    resp = await client.get(
        "/v1/reports/audit-log.csv",
        params={"start": "2026-01-01T00:00:00Z", "end": "2026-12-31T00:00:00Z"},
        headers=_auth_headers(["logistics_viewer"]),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_tracking_force_refresh(client, db_session, seeded_carriers, monkeypatch):

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.services.serviceability.get_redis", lambda: fake_redis)

    shipment = Shipment(
        id=uuid.UUID("99999999-8888-7777-6666-aaaaaaaaaaaa"),
        order_id=uuid.UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff"),
        carrier_id=seeded_carriers["delhivery"].id,
        carrier_awb="DL-TRACK-1",
        shipment_type=ShipmentType.FORWARD,
        status=ShipmentStatus.IN_TRANSIT,
        origin_pincode="560001",
        destination_pincode="110001",
        weight_kg=1.0,
        cod_amount=0,
        meta={},
    )
    db_session.add(shipment)
    await db_session.commit()

    from tests.conftest import FakeAdapter

    adapter = FakeAdapter("delhivery", awb="DL-TRACK-1")
    monkeypatch.setattr("app.services.tracking.get_adapter", lambda code: adapter)
    monkeypatch.setattr("app.services.tracking.sync_order_shipment_status", AsyncMock(return_value=True))
    monkeypatch.setattr("app.services.tracking.notify_shipment_status_change", AsyncMock(return_value=None))

    resp = await client.get(
        f"/v1/shipments/{shipment.id}/tracking",
        params={"force_refresh": "true"},
        headers=_auth_headers(["logistics_ops"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_status"] == "delivered"
    assert len(body["events"]) == 1


@pytest.mark.asyncio
async def test_tracking_shipment_not_found(client):
    resp = await client.get(
        "/v1/shipments/00000000-0000-0000-0000-000000000000/tracking",
        headers=_auth_headers(["logistics_ops"]),
    )
    assert resp.status_code == 404
