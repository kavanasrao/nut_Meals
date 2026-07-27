"""Integration tests for Address API."""
import pytest

ADDRESS_PAYLOAD = {
    "label": "Home",
    "full_name": "Test User",
    "phone": "9876543210",
    "line1": "456 Park Ave",
    "city": "Bengaluru",
    "state": "Karnataka",
    "pincode": "560001",
}


class TestAddressAPI:
    @pytest.mark.asyncio
    async def test_create_address(self, client):
        resp = await client.post("/api/v1/addresses", json=ADDRESS_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["city"] == "Bengaluru"

    @pytest.mark.asyncio
    async def test_list_addresses(self, client):
        await client.post("/api/v1/addresses", json=ADDRESS_PAYLOAD)
        await client.post("/api/v1/addresses", json={**ADDRESS_PAYLOAD, "label": "Office"})
        resp = await client.get("/api/v1/addresses")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_update_address(self, client):
        create = await client.post("/api/v1/addresses", json=ADDRESS_PAYLOAD)
        addr_id = create.json()["id"]
        resp = await client.put(
            f"/api/v1/addresses/{addr_id}",
            json={**ADDRESS_PAYLOAD, "city": "Mysuru"},
        )
        assert resp.status_code == 200
        assert resp.json()["city"] == "Mysuru"

    @pytest.mark.asyncio
    async def test_delete_address(self, client):
        create = await client.post("/api/v1/addresses", json=ADDRESS_PAYLOAD)
        addr_id = create.json()["id"]
        resp = await client.delete(f"/api/v1/addresses/{addr_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_set_default(self, client):
        a1 = (await client.post("/api/v1/addresses", json=ADDRESS_PAYLOAD)).json()
        a2 = (await client.post("/api/v1/addresses", json={**ADDRESS_PAYLOAD, "label": "Office"})).json()
        resp = await client.patch(f"/api/v1/addresses/{a2['id']}/default")
        assert resp.status_code == 200
        assert resp.json()["is_default"] is True

    @pytest.mark.asyncio
    async def test_invalid_pincode_rejected(self, client):
        resp = await client.post("/api/v1/addresses", json={**ADDRESS_PAYLOAD, "pincode": "ABCDE"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_phone_rejected(self, client):
        resp = await client.post("/api/v1/addresses", json={**ADDRESS_PAYLOAD, "phone": "abc"})
        assert resp.status_code == 422
