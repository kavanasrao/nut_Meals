"""Integration tests for Cart API."""
import pytest

PRODUCT_PAYLOAD = {
    "product_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "product_name": "Cashew Butter",
    "unit_price": "250.00",
    "quantity": 2,
}


class TestCartAPI:
    @pytest.mark.asyncio
    async def test_get_empty_cart(self, client):
        resp = await client.get("/api/v1/cart")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert float(data["subtotal"]) == 0.0

    @pytest.mark.asyncio
    async def test_add_item(self, client):
        resp = await client.post("/api/v1/cart/items", json=PRODUCT_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

    @pytest.mark.asyncio
    async def test_upsert_quantity(self, client):
        await client.post("/api/v1/cart/items", json=PRODUCT_PAYLOAD)
        resp = await client.post("/api/v1/cart/items", json={**PRODUCT_PAYLOAD, "quantity": 1})
        assert resp.json()["items"][0]["quantity"] == 3

    @pytest.mark.asyncio
    async def test_update_item(self, client):
        add = await client.post("/api/v1/cart/items", json=PRODUCT_PAYLOAD)
        item_id = add.json()["items"][0]["id"]
        resp = await client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 5})
        assert resp.status_code == 200
        assert resp.json()["items"][0]["quantity"] == 5

    @pytest.mark.asyncio
    async def test_remove_item(self, client):
        add = await client.post("/api/v1/cart/items", json=PRODUCT_PAYLOAD)
        item_id = add.json()["items"][0]["id"]
        resp = await client.delete(f"/api/v1/cart/items/{item_id}")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_clear_cart(self, client):
        await client.post("/api/v1/cart/items", json=PRODUCT_PAYLOAD)
        resp = await client.delete("/api/v1/cart")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_apply_coupon(self, client):
        await client.post("/api/v1/cart/items", json=PRODUCT_PAYLOAD)
        resp = await client.post("/api/v1/cart/coupon", json={"coupon_code": "SAVE10"})
        assert resp.status_code == 200
        assert resp.json()["coupon_code"] == "SAVE10"

    @pytest.mark.asyncio
    async def test_invalid_quantity_rejected(self, client):
        resp = await client.post("/api/v1/cart/items", json={**PRODUCT_PAYLOAD, "quantity": 0})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated_rejected(self):
        """HTTPBearer returns 403 when Authorization header is absent."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/v1/cart")
        # FastAPI HTTPBearer returns 403 (Forbidden) when no credentials provided
        assert resp.status_code in (401, 403)  # HTTPBearer version-dependent

    @pytest.mark.asyncio
    async def test_subtotal_is_correct(self, client):
        await client.post("/api/v1/cart/items", json=PRODUCT_PAYLOAD)
        resp = await client.get("/api/v1/cart")
        assert float(resp.json()["subtotal"]) == 500.0   # 250 * 2
