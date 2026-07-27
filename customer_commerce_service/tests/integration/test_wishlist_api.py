"""Integration tests for Wishlist API."""
import pytest

ITEM = {
    "product_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "product_name": "Pistachio Mix",
    "unit_price": "399.00",
}


class TestWishlistAPI:
    @pytest.mark.asyncio
    async def test_empty_wishlist(self, client):
        resp = await client.get("/api/v1/wishlist")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_add_item(self, client):
        resp = await client.post("/api/v1/wishlist", json=ITEM)
        assert resp.status_code == 201
        assert resp.json()["product_name"] == "Pistachio Mix"

    @pytest.mark.asyncio
    async def test_add_duplicate_is_idempotent(self, client):
        await client.post("/api/v1/wishlist", json=ITEM)
        await client.post("/api/v1/wishlist", json=ITEM)
        resp = await client.get("/api/v1/wishlist")
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_remove_item(self, client):
        await client.post("/api/v1/wishlist", json=ITEM)
        resp = await client.delete(f"/api/v1/wishlist/{ITEM['product_id']}")
        assert resp.status_code == 204
        assert (await client.get("/api/v1/wishlist")).json()["total"] == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_raises(self, client):
        resp = await client.delete(f"/api/v1/wishlist/{ITEM['product_id']}")
        assert resp.status_code == 404
