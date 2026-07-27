"""Tests for the core (pre-existing) user routes: register, login, refresh,
profile, change-password, and admin block/unblock/list/stats."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.user import User, UserRole
from tests.conftest import auth_headers, create_user

pytestmark = pytest.mark.asyncio


async def test_register_creates_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/users/register",
        json={"name": "New User", "email": "newuser@example.com", "password": "SuperSecret123"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "newuser@example.com"


async def test_register_duplicate_email_fails(client: AsyncClient, user: User):
    resp = await client.post(
        "/api/v1/users/register",
        json={"name": "Dup", "email": user.email, "password": "SuperSecret123"},
    )
    assert resp.status_code == 409


async def test_login_with_correct_credentials(client: AsyncClient, db_session):
    await create_user(db_session, email="login@example.com", password="CorrectHorse123")
    resp = await client.post(
        "/api/v1/users/login", json={"email": "login@example.com", "password": "CorrectHorse123"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_with_wrong_password_fails(client: AsyncClient, user: User):
    resp = await client.post(
        "/api/v1/users/login", json={"email": user.email, "password": "WrongPassword"}
    )
    assert resp.status_code == 401


async def test_login_blocked_user_fails(client: AsyncClient, db_session):
    blocked = await create_user(
        db_session, email="blocked@example.com", password="SomePassword123", is_blocked=True
    )
    resp = await client.post(
        "/api/v1/users/login", json={"email": blocked.email, "password": "SomePassword123"}
    )
    assert resp.status_code == 403


async def test_get_me(client: AsyncClient, user: User):
    resp = await client.get("/api/v1/users/me", headers=auth_headers(user))
    assert resp.status_code == 200
    assert resp.json()["id"] == str(user.id)


async def test_change_password(client: AsyncClient, user: User):
    resp = await client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": "SuperSecret123", "new_password": "AnotherPassword123"},
        headers=auth_headers(user),
    )
    assert resp.status_code == 200


async def test_admin_can_block_and_unblock_user(client: AsyncClient, user: User, admin: User):
    block_resp = await client.patch(f"/api/v1/users/{user.id}/block")
    assert block_resp.status_code == 200
    assert block_resp.json()["is_blocked"] is True

    unblock_resp = await client.patch(f"/api/v1/users/{user.id}/unblock")
    assert unblock_resp.status_code == 200
    assert unblock_resp.json()["is_blocked"] is False


async def test_user_stats(client: AsyncClient, user: User, admin: User):
    resp = await client.get("/api/v1/users/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
