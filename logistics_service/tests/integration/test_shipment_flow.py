"""
Integration tests exercising the FastAPI routes end-to-end (in-memory SQLite
+ fakeredis + fake carrier adapters, real HTTP layer via httpx ASGITransport).
"""
import jwt
import pytest

from app.config import get_settings

settings = get_settings()


def _auth_headers(roles: list[str]) -> dict:
    token = jwt.encode({"sub": "test-user", "roles": roles}, key="", algorithm="none")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def patch_jwt_no_verify(monkeypatch):
    # Test environment doesn't have a real signing key; disable signature
    # verification consistent with settings.jwt_public_key == "".
    monkeypatch.setattr(settings, "jwt_public_key", "")


@pytest.mark.asyncio
async def test_list_carriers_requires_auth(client):
    resp = await client.get("/v1/carriers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_carriers_returns_seeded_carriers(client, seeded_carriers):
    resp = await client.get("/v1/carriers", headers=_auth_headers(["logistics_viewer"]))
    assert resp.status_code == 200
    codes = {c["code"] for c in resp.json()}
    assert codes == {"delhivery", "india_post"}


@pytest.mark.asyncio
async def test_list_carriers_forbidden_without_role(client, seeded_carriers):
    resp = await client.get("/v1/carriers", headers=_auth_headers(["some_other_role"]))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_serviceability_endpoint(client, seeded_carriers, monkeypatch):
    import fakeredis.aioredis

    from app.services import serviceability as serviceability_module

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(serviceability_module, "get_redis", lambda: fake_redis)

    resp = await client.post(
        "/v1/carriers/serviceability",
        json={"origin_pincode": "560001", "destination_pincode": "110001", "weight_kg": 1.0},
        headers=_auth_headers(["logistics_ops"]),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["origin_pincode"] == "560001"
    assert "options" in body


@pytest.mark.asyncio
async def test_create_shipment_and_fetch_it(client, seeded_carriers, monkeypatch):
    import fakeredis.aioredis

    from app.services import allocation as allocation_module
    from app.services import serviceability as serviceability_module

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(serviceability_module, "get_redis", lambda: fake_redis)

    from tests.conftest import FakeAdapter
    from app.models.carrier import CarrierCode

    adapters = {
        CarrierCode.DELHIVERY: FakeAdapter("delhivery", cost=40, hours=48, awb="DL-API-1"),
        CarrierCode.INDIA_POST: FakeAdapter("india_post", cost=60, hours=96, awb="IP-API-1"),
    }
    monkeypatch.setattr(allocation_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "get_adapter", lambda code: adapters[code])
    monkeypatch.setattr(serviceability_module, "all_carrier_codes", lambda: list(adapters.keys()))

    create_resp = await client.post(
        "/v1/shipments",
        json={
            "order_id": "aaaaaaaa-bbbb-cccc-dddd-111111111111",
            "origin_pincode": "560001",
            "destination_pincode": "110001",
            "weight_kg": 1.5,
            "cod_amount": 0,
        },
        headers=_auth_headers(["logistics_ops"]),
    )
    assert create_resp.status_code == 201
    shipment = create_resp.json()
    assert shipment["carrier_awb"] == "DL-API-1"

    get_resp = await client.get(
        f"/v1/shipments/{shipment['id']}", headers=_auth_headers(["logistics_viewer"])
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == shipment["id"]


@pytest.mark.asyncio
async def test_get_shipment_not_found(client, seeded_carriers):
    resp = await client.get(
        "/v1/shipments/00000000-0000-0000-0000-000000000000",
        headers=_auth_headers(["logistics_viewer"]),
    )
    assert resp.status_code == 404
