"""Tests for customer preference endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


async def test_get_preferences_creates_defaults_on_first_access(client: AsyncClient, user: User):
    resp = await client.get("/api/v1/preferences", headers=auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "en"
    assert body["dark_mode"] is False
    assert body["marketing_opt_in"] is True


async def test_update_preferences_partial(client: AsyncClient, user: User):
    headers = auth_headers(user)
    await client.get("/api/v1/preferences", headers=headers)

    resp = await client.patch(
        "/api/v1/preferences", json={"dark_mode": True, "language": "hi"}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["dark_mode"] is True
    assert body["language"] == "hi"
    # Untouched fields keep their previous values.
    assert body["marketing_opt_in"] is True


async def test_update_marketing_opt_out(client: AsyncClient, user: User):
    headers = auth_headers(user)
    resp = await client.patch(
        "/api/v1/preferences", json={"marketing_opt_in": False}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["marketing_opt_in"] is False


async def test_preferences_require_authentication(client: AsyncClient):
    resp = await client.get("/api/v1/preferences")
    assert resp.status_code == 401
