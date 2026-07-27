import uuid

import pytest

from app.core.security import CurrentUser, get_current_user
from app.main import app

pytestmark = pytest.mark.integration


async def test_create_and_get_vendor(client):
    resp = await client.post(
        "/api/v1/vendors",
        json={"name": "Fresh Farms Ltd", "email": "contact@freshfarms.test"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Fresh Farms Ltd"
    assert body["status"] == "active"

    get_resp = await client.get(f"/api/v1/vendors/{body['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]


async def test_get_nonexistent_vendor_404(client):
    resp = await client.get(f"/api/v1/vendors/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_list_vendors_pagination(client):
    for i in range(3):
        await client.post(
            "/api/v1/vendors", json={"name": f"Vendor {i}", "email": f"v{i}@test.com"}
        )
    resp = await client.get("/api/v1/vendors", params={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["items"]) == 2


async def test_update_vendor(client):
    create_resp = await client.post(
        "/api/v1/vendors", json={"name": "To Update", "email": "u@test.com"}
    )
    vendor_id = create_resp.json()["id"]
    patch_resp = await client.patch(
        f"/api/v1/vendors/{vendor_id}", json={"status": "inactive"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "inactive"


async def test_delete_vendor(client):
    create_resp = await client.post(
        "/api/v1/vendors", json={"name": "To Delete", "email": "d@test.com"}
    )
    vendor_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/vendors/{vendor_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/vendors/{vendor_id}")
    assert get_resp.status_code == 404


async def test_ledger_add_and_read(client):
    create_resp = await client.post(
        "/api/v1/vendors", json={"name": "Ledger Vendor", "email": "l@test.com"}
    )
    vendor_id = create_resp.json()["id"]

    entry_resp = await client.post(
        f"/api/v1/vendors/{vendor_id}/ledger",
        json={
            "entry_type": "debit",
            "source": "opening_balance",
            "amount": "500.00",
            "description": "Opening balance",
        },
    )
    assert entry_resp.status_code == 201
    assert entry_resp.json()["balance_after"] == "500.00"

    ledger_resp = await client.get(f"/api/v1/vendors/{vendor_id}/ledger")
    assert ledger_resp.status_code == 200
    body = ledger_resp.json()
    assert body["current_balance"] == "500.00"
    assert len(body["entries"]) == 1


async def test_finance_viewer_cannot_write(client, db_session):
    """RBAC: a read-only role should be rejected from write endpoints."""

    async def override_finance_viewer():
        return CurrentUser(id=uuid.uuid4(), email="fv@test.com", roles=["finance_viewer"])

    app.dependency_overrides[get_current_user] = override_finance_viewer
    try:
        resp = await client.post(
            "/api/v1/vendors", json={"name": "Should Fail", "email": "sf@test.com"}
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def test_missing_bearer_token_401():
    """No auth override -> real dependency should reject with 401."""
    from httpx import ASGITransport, AsyncClient

    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/vendors")
    assert resp.status_code == 401
