"""Tests for user audit log generation and retrieval."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import auth_headers

pytestmark = pytest.mark.asyncio


async def test_profile_update_writes_audit_log(client: AsyncClient, user: User):
    headers = auth_headers(user)
    resp = await client.patch("/api/v1/users/me", json={"name": "New Name"}, headers=headers)
    assert resp.status_code == 200

    logs_resp = await client.get("/api/v1/audit/me", headers=headers)
    assert logs_resp.status_code == 200
    actions = [log["action"] for log in logs_resp.json()["logs"]]
    assert "profile_update" in actions


async def test_address_create_writes_audit_log(client: AsyncClient, user: User):
    headers = auth_headers(user)
    await client.post(
        "/api/v1/addresses",
        json={
            "label": "Home",
            "full_name": "Jane Doe",
            "phone": "+919876543210",
            "line1": "123 MG Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "country": "India",
            "postal_code": "560001",
        },
        headers=headers,
    )

    logs_resp = await client.get("/api/v1/audit/me", headers=headers)
    actions = [log["action"] for log in logs_resp.json()["logs"]]
    assert "address_create" in actions


async def test_non_admin_cannot_view_another_users_audit_log(client: AsyncClient, user: User):
    resp = await client.get(f"/api/v1/audit/{user.id}", headers=auth_headers(user))
    assert resp.status_code == 403


async def test_admin_can_view_any_users_audit_log(client: AsyncClient, user: User, admin: User):
    headers = auth_headers(user)
    await client.patch("/api/v1/users/me", json={"name": "Changed"}, headers=headers)

    resp = await client.get(f"/api/v1/audit/{user.id}", headers=auth_headers(admin))
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


async def test_audit_me_requires_authentication(client: AsyncClient):
    resp = await client.get("/api/v1/audit/me")
    assert resp.status_code == 401
