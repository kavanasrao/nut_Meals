"""Tests for the redirect manager: CRUD, public resolution, and usage logging."""
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_redirect_requires_admin(client, viewer_headers):
    resp = await client.post(
        "/api/v1/redirects",
        json={"source_path": "/old-page", "target_path": "/new-page", "redirect_type": 301},
        headers=viewer_headers,
    )
    assert resp.status_code == 403


async def test_create_and_resolve_redirect(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/redirects",
        json={"source_path": "/old-almonds", "target_path": "/products/almonds", "redirect_type": 301},
        headers=admin_headers,
    )
    assert create_resp.status_code == 201

    with patch("app.tasks.redirect_tasks.sync_redirect_analytics_task.delay") as mock_delay:
        resolve_resp = await client.get("/api/v1/redirects/resolve", params={"path": "/old-almonds"})
        assert resolve_resp.status_code == 200
        body = resolve_resp.json()
        assert body["found"] is True
        assert body["target_path"] == "/products/almonds"
        assert body["redirect_type"] == 301
        mock_delay.assert_called_once()


async def test_resolve_unknown_path_returns_not_found(client):
    resp = await client.get("/api/v1/redirects/resolve", params={"path": "/does-not-exist"})
    assert resp.status_code == 200
    assert resp.json() == {"found": False, "target_path": None, "redirect_type": None}


async def test_duplicate_source_path_conflict(client, admin_headers):
    payload = {"source_path": "/dup-path", "target_path": "/target-a", "redirect_type": 301}
    first = await client.post("/api/v1/redirects", json=payload, headers=admin_headers)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/redirects",
        json={**payload, "target_path": "/target-b"},
        headers=admin_headers,
    )
    assert second.status_code == 409


async def test_update_redirect_deactivates_it(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/redirects",
        json={"source_path": "/temp-page", "target_path": "/permanent-page", "redirect_type": 302},
        headers=admin_headers,
    )
    redirect_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/redirects/{redirect_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False

    resolve_resp = await client.get("/api/v1/redirects/resolve", params={"path": "/temp-page"})
    assert resolve_resp.json()["found"] is False


async def test_delete_redirect(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/redirects",
        json={"source_path": "/to-delete", "target_path": "/somewhere", "redirect_type": 301},
        headers=admin_headers,
    )
    redirect_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/redirects/{redirect_id}", headers=admin_headers)
    assert delete_resp.status_code == 204

    list_resp = await client.get("/api/v1/redirects", headers=admin_headers)
    ids = [r["id"] for r in list_resp.json()]
    assert redirect_id not in ids


async def test_invalid_redirect_type_rejected(client, admin_headers):
    resp = await client.post(
        "/api/v1/redirects",
        json={"source_path": "/bad-type", "target_path": "/x", "redirect_type": 404},
        headers=admin_headers,
    )
    assert resp.status_code == 422
