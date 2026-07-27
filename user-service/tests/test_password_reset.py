"""Tests for the forgot-password / reset-password flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.auth_service import _hash_token
from tests.conftest import create_user

pytestmark = pytest.mark.asyncio


async def test_forgot_password_known_email_queues_email(
    client: AsyncClient, db_session: AsyncSession, user: User, stub_notification_tasks
):
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert resp.status_code == 200
    assert len(stub_notification_tasks["reset"]) == 1
    assert stub_notification_tasks["reset"][0]["email"] == user.email


async def test_forgot_password_unknown_email_still_returns_generic_success(
    client: AsyncClient, stub_notification_tasks
):
    resp = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200
    assert len(stub_notification_tasks["reset"]) == 0


async def test_reset_password_with_valid_token_succeeds(
    client: AsyncClient, db_session: AsyncSession, user: User
):
    raw_token = "unit-test-raw-token-abcdef123456"
    token = PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(token)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "BrandNewPassword123"},
    )
    assert resp.status_code == 200

    await db_session.refresh(user)
    assert verify_password("BrandNewPassword123", user.password_hash)


async def test_reset_password_with_expired_token_fails(
    client: AsyncClient, db_session: AsyncSession, user: User
):
    raw_token = "expired-token-1234567890"
    token = PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(token)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "BrandNewPassword123"},
    )
    assert resp.status_code == 400


async def test_reset_password_with_invalid_token_fails(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "totally-made-up-token-000000", "new_password": "BrandNewPassword123"},
    )
    assert resp.status_code == 400


async def test_reset_password_token_is_single_use(
    client: AsyncClient, db_session: AsyncSession, user: User
):
    raw_token = "single-use-token-99999999"
    token = PasswordResetToken(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(token)
    await db_session.commit()

    first = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "FirstNewPassword123"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw_token, "new_password": "SecondNewPassword123"},
    )
    assert second.status_code == 400
