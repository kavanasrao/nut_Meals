"""Tests for product & category CRUD, RBAC enforcement, and pagination."""
import uuid

import pytest
from unittest.mock import AsyncMock, patch

pytestmark = pytest.mark.asyncio


async def _create_category(client, admin_headers, name="Nuts"):
    resp = await client.post(
        "/api/v1/categories",
        json={"name": name, "slug": name.lower(), "description": "desc"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def test_create_product_requires_admin_role(client, viewer_headers):
    resp = await client.post(
        "/api/v1/products",
        json={
            "sku": "SKU-001",
            "name": "Almonds",
            "slug": "almonds",
            "base_price": "9.99",
        },
        headers=viewer_headers,
    )
    assert resp.status_code == 403


async def test_create_product_unauthenticated(client):
    resp = await client.post(
        "/api/v1/products",
        json={"sku": "SKU-002", "name": "Cashews", "slug": "cashews", "base_price": "5.00"},
    )
    assert resp.status_code == 401


async def test_create_and_get_product(client, admin_headers):
    category = await _create_category(client, admin_headers, "Snacks")

    create_resp = await client.post(
        "/api/v1/products",
        json={
            "sku": "SKU-100",
            "name": "Roasted Cashews",
            "slug": "roasted-cashews",
            "base_price": "12.50",
            "category_id": category["id"],
            "attributes": [{"name": "roast_level", "value": "medium"}],
            "variants": [{"sku": "SKU-100-250G", "packaging": "250g bag", "price_delta": "0.00"}],
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    product = create_resp.json()
    assert product["sku"] == "SKU-100"
    assert len(product["attributes"]) == 1
    assert len(product["variants"]) == 1

    with patch(
        "app.services.inventory_client.InventoryClient.get_stock_for_skus",
        new=AsyncMock(return_value={"SKU-100-250G": {"is_in_stock": True, "quantity_available": 42}}),
    ):
        get_resp = await client.get(f"/api/v1/products/{product['id']}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["variants"][0]["is_in_stock"] is True
    assert detail["variants"][0]["quantity_available"] == 42
    assert detail["average_rating"] == 0.0


async def test_duplicate_sku_rejected(client, admin_headers):
    payload = {"sku": "SKU-DUPE", "name": "Pistachios", "slug": "pistachios", "base_price": "8.00"}
    first = await client.post("/api/v1/products", json=payload, headers=admin_headers)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/products",
        json={**payload, "slug": "pistachios-2"},
        headers=admin_headers,
    )
    assert second.status_code == 409


async def test_get_nonexistent_product_returns_404(client):
    resp = await client.get(f"/api/v1/products/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_update_product(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/products",
        json={"sku": "SKU-200", "name": "Walnuts", "slug": "walnuts", "base_price": "10.00"},
        headers=admin_headers,
    )
    product_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/products/{product_id}",
        json={"name": "Organic Walnuts", "base_price": "11.50"},
        headers=admin_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Organic Walnuts"
    assert update_resp.json()["base_price"] == "11.50"


async def test_delete_product(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/products",
        json={"sku": "SKU-300", "name": "Pecans", "slug": "pecans", "base_price": "13.00"},
        headers=admin_headers,
    )
    product_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/products/{product_id}", headers=admin_headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/products/{product_id}")
    assert get_resp.status_code == 404


async def test_list_products_pagination(client, admin_headers):
    for i in range(5):
        await client.post(
            "/api/v1/products",
            json={"sku": f"SKU-LIST-{i}", "name": f"Product {i}", "slug": f"product-{i}", "base_price": "1.00"},
            headers=admin_headers,
        )

    resp = await client.get("/api/v1/products?page=1&page_size=2")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] >= 5


async def test_create_category_duplicate_slug_conflict(client, admin_headers):
    await _create_category(client, admin_headers, "Dried Fruit")
    dup_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Dried Fruit Again", "slug": "dried fruit"},
        headers=admin_headers,
    )
    assert dup_resp.status_code == 409
