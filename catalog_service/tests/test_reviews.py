"""Tests for review submission, moderation workflow, and aggregate rating recompute."""
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.asyncio


async def _create_product(client, admin_headers, sku="SKU-REV-1"):
    resp = await client.post(
        "/api/v1/products",
        json={"sku": sku, "name": "Trail Mix", "slug": f"{sku.lower()}-slug", "base_price": "6.49"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def test_submit_review_starts_pending(client, admin_headers, customer_headers):
    product = await _create_product(client, admin_headers)
    headers, _ = customer_headers

    resp = await client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json={"customer_name": "Jane", "rating": 5, "title": "Great!", "body": "Loved it."},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"


async def test_pending_review_not_publicly_visible(client, admin_headers, customer_headers):
    product = await _create_product(client, admin_headers, sku="SKU-REV-2")
    headers, _ = customer_headers
    await client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json={"customer_name": "Bob", "rating": 4},
        headers=headers,
    )

    public_resp = await client.get(f"/api/v1/products/{product['id']}/reviews")
    assert public_resp.status_code == 200
    assert public_resp.json() == []


async def test_moderator_can_approve_review_and_aggregate_updates(
    client, admin_headers, customer_headers, moderator_headers
):
    product = await _create_product(client, admin_headers, sku="SKU-REV-3")
    headers, _ = customer_headers

    review_resp = await client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json={"customer_name": "Ann", "rating": 5},
        headers=headers,
    )
    review_id = review_resp.json()["id"]

    with patch("app.tasks.moderation_tasks.recompute_rating_aggregate_task.delay") as mock_delay:
        moderate_resp = await client.post(
            f"/api/v1/reviews/{review_id}/moderate",
            json={"status": "approved", "moderation_notes": "Looks genuine"},
            headers=moderator_headers,
        )
        assert moderate_resp.status_code == 200
        assert moderate_resp.json()["status"] == "approved"
        mock_delay.assert_called_once()

    public_resp = await client.get(f"/api/v1/products/{product['id']}/reviews")
    assert len(public_resp.json()) == 1

    rating_resp = await client.get(f"/api/v1/products/{product['id']}/reviews/rating")
    assert rating_resp.status_code == 200
    assert rating_resp.json()["average_rating"] == 5.0
    assert rating_resp.json()["review_count"] == 1


async def test_customer_cannot_moderate_review(client, admin_headers, customer_headers):
    product = await _create_product(client, admin_headers, sku="SKU-REV-4")
    headers, _ = customer_headers
    review_resp = await client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json={"customer_name": "Ed", "rating": 3},
        headers=headers,
    )
    review_id = review_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/reviews/{review_id}/moderate",
        json={"status": "approved"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_moderator_can_view_pending_queue(client, admin_headers, customer_headers, moderator_headers):
    product = await _create_product(client, admin_headers, sku="SKU-REV-5")
    headers, _ = customer_headers
    await client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json={"customer_name": "Sam", "rating": 2},
        headers=headers,
    )

    resp = await client.get("/api/v1/reviews/pending", headers=moderator_headers)
    assert resp.status_code == 200
    assert any(r["product_id"] == product["id"] for r in resp.json())


async def test_review_rating_out_of_range_rejected(client, admin_headers, customer_headers):
    product = await _create_product(client, admin_headers, sku="SKU-REV-6")
    headers, _ = customer_headers
    resp = await client.post(
        f"/api/v1/products/{product['id']}/reviews",
        json={"customer_name": "Max", "rating": 7},
        headers=headers,
    )
    assert resp.status_code == 422
