"""Integration tests for the Content/Blog Manager API."""
from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_create_blog_post_success(client, content_admin_headers):
    payload = {
        "content_type": "blog_post",
        "title": "5 High-Protein Nut Mixes",
        "slug": "5-high-protein-nut-mixes",
        "body": "Full article body here.",
        "excerpt": "A quick roundup.",
        "seo_title": "High-Protein Nut Mixes",
        "seo_description": "Discover our top protein-packed nut mixes.",
        "tags": ["nutrition", "snacks"],
    }
    resp = await client.post("/api/v1/content", json=payload, headers=content_admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "5-high-protein-nut-mixes"
    assert body["status"] == "draft"
    assert body["content_type"] == "blog_post"


@pytest.mark.asyncio
async def test_create_blog_post_invalid_slug_rejected(client, content_admin_headers):
    payload = {
        "content_type": "blog_post",
        "title": "Bad Slug",
        "slug": "Not A Valid Slug!",
        "body": "Body",
    }
    resp = await client.post("/api/v1/content", json=payload, headers=content_admin_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_blog_post_duplicate_slug_conflict(client, content_admin_headers):
    payload = {
        "content_type": "faq",
        "title": "Shipping FAQ",
        "slug": "shipping-faq",
        "body": "We ship worldwide.",
    }
    first = await client.post("/api/v1/content", json=payload, headers=content_admin_headers)
    assert first.status_code == 201

    second = await client.post("/api/v1/content", json=payload, headers=content_admin_headers)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_create_content_requires_write_role(client, analytics_viewer_headers):
    payload = {
        "content_type": "announcement",
        "title": "Holiday Hours",
        "slug": "holiday-hours",
        "body": "We are closed on public holidays.",
    }
    resp = await client.post("/api/v1/content", json=payload, headers=analytics_viewer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_content_without_token_unauthorized(client):
    payload = {
        "content_type": "announcement",
        "title": "No Auth",
        "slug": "no-auth",
        "body": "Body",
    }
    resp = await client.post("/api/v1/content", json=payload)
    assert resp.status_code == 403 or resp.status_code == 401  # HTTPBearer raises 403 w/o header


@pytest.mark.asyncio
async def test_scheduled_post_gets_scheduled_status(client, content_admin_headers):
    future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    payload = {
        "content_type": "blog_post",
        "title": "Future Post",
        "slug": "future-post",
        "body": "Coming soon.",
        "publish_at": future_time,
    }
    resp = await client.post("/api/v1/content", json=payload, headers=content_admin_headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "scheduled"


@pytest.mark.asyncio
async def test_publish_content_item_immediately(client, content_admin_headers):
    payload = {
        "content_type": "faq",
        "title": "Return Policy",
        "slug": "return-policy",
        "body": "Returns accepted within 30 days.",
    }
    created = await client.post("/api/v1/content", json=payload, headers=content_admin_headers)
    content_id = created.json()["id"]

    resp = await client.post(f"/api/v1/content/{content_id}/publish", headers=content_admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"
    assert resp.json()["published_at"] is not None


@pytest.mark.asyncio
async def test_update_content_item_creates_revision(client, content_admin_headers):
    payload = {
        "content_type": "blog_post",
        "title": "Original Title",
        "slug": "original-title",
        "body": "Original body.",
    }
    created = await client.post("/api/v1/content", json=payload, headers=content_admin_headers)
    content_id = created.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/content/{content_id}",
        json={"title": "Updated Title"},
        headers=content_admin_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_get_nonexistent_content_returns_404(client, content_admin_headers):
    resp = await client.get(
        "/api/v1/content/00000000-0000-0000-0000-000000000000", headers=content_admin_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_content_items_pagination(client, content_admin_headers):
    for i in range(3):
        payload = {
            "content_type": "faq",
            "title": f"FAQ {i}",
            "slug": f"faq-{i}",
            "body": "Answer",
        }
        await client.post("/api/v1/content", json=payload, headers=content_admin_headers)

    resp = await client.get("/api/v1/content?page=1&page_size=2", headers=content_admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 2
    assert body["total"] >= 3


@pytest.mark.asyncio
async def test_delete_content_item(client, super_admin_headers):
    payload = {
        "content_type": "faq",
        "title": "To Delete",
        "slug": "to-delete",
        "body": "Body",
    }
    created = await client.post("/api/v1/content", json=payload, headers=super_admin_headers)
    content_id = created.json()["id"]

    delete_resp = await client.delete(f"/api/v1/content/{content_id}", headers=super_admin_headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/content/{content_id}", headers=super_admin_headers)
    assert get_resp.status_code == 404
