"""Tests for SEO metadata CRUD and JSON-LD structured data generation."""
import pytest

pytestmark = pytest.mark.asyncio


async def _create_product(client, admin_headers, sku="SKU-SEO-1"):
    resp = await client.post(
        "/api/v1/products",
        json={"sku": sku, "name": "Almond Butter", "slug": f"{sku.lower()}-slug", "base_price": "7.99"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def test_get_seo_metadata_404_when_missing(client, admin_headers):
    product = await _create_product(client, admin_headers)
    resp = await client.get(f"/api/v1/products/{product['id']}/seo")
    assert resp.status_code == 404


async def test_upsert_and_get_seo_metadata(client, admin_headers):
    product = await _create_product(client, admin_headers, sku="SKU-SEO-2")

    upsert_resp = await client.put(
        f"/api/v1/products/{product['id']}/seo",
        json={
            "meta_title": "Buy Almond Butter Online",
            "meta_description": "Smooth, creamy almond butter made fresh.",
            "og_image_url": "https://cdn.nutmeals.com/almond-butter.jpg",
        },
        headers=admin_headers,
    )
    assert upsert_resp.status_code == 200
    body = upsert_resp.json()
    assert body["meta_title"] == "Buy Almond Butter Online"
    assert body["structured_data"]["@type"] == "Product"
    assert body["structured_data"]["offers"]["price"] == "7.99"
    assert body["structured_data"]["image"] == "https://cdn.nutmeals.com/almond-butter.jpg"

    get_resp = await client.get(f"/api/v1/products/{product['id']}/seo")
    assert get_resp.status_code == 200
    assert get_resp.json()["meta_title"] == "Buy Almond Butter Online"


async def test_upsert_seo_metadata_requires_admin(client, viewer_headers, admin_headers):
    product = await _create_product(client, admin_headers, sku="SKU-SEO-3")
    resp = await client.put(
        f"/api/v1/products/{product['id']}/seo",
        json={"meta_title": "Hacked title"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


async def test_seo_metadata_for_unknown_product_404(client, admin_headers):
    import uuid

    resp = await client.put(
        f"/api/v1/products/{uuid.uuid4()}/seo",
        json={"meta_title": "Ghost product"},
        headers=admin_headers,
    )
    assert resp.status_code == 404
