"""Tests for Google Sign-In social login.

Google's tokeninfo endpoint is stubbed via monkeypatching
`AuthService._verify_google_id_token` so tests never call out to Google.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_account import SocialAccount, SocialProvider
from app.models.user import User

pytestmark = pytest.mark.asyncio


def _stub_google_claims(monkeypatch, *, sub: str, email: str):
    async def _fake_verify(self, id_token: str):
        return {"sub": sub, "email": email, "aud": "test-client-id"}

    monkeypatch.setattr(
        "app.services.auth_service.AuthService._verify_google_id_token", _fake_verify
    )


async def test_google_login_creates_new_user_on_first_sign_in(
    client: AsyncClient, db_session: AsyncSession, monkeypatch, stub_notification_tasks
):
    _stub_google_claims(monkeypatch, sub="google-sub-123", email="googleuser@example.com")

    resp = await client.post("/api/v1/auth/google", json={"id_token": "fake-id-token"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body

    result = await db_session.execute(select(User).where(User.email == "googleuser@example.com"))
    user = result.scalar_one_or_none()
    assert user is not None

    result = await db_session.execute(
        select(SocialAccount).where(SocialAccount.provider_user_id == "google-sub-123")
    )
    social = result.scalar_one_or_none()
    assert social is not None
    assert social.provider == SocialProvider.GOOGLE
    assert social.user_id == user.id


async def test_google_login_reuses_existing_linked_account(
    client: AsyncClient, db_session: AsyncSession, monkeypatch, stub_notification_tasks
):
    _stub_google_claims(monkeypatch, sub="google-sub-456", email="repeat@example.com")

    first = await client.post("/api/v1/auth/google", json={"id_token": "fake-id-token"})
    assert first.status_code == 200

    second = await client.post("/api/v1/auth/google", json={"id_token": "fake-id-token"})
    assert second.status_code == 200

    result = await db_session.execute(
        select(SocialAccount).where(SocialAccount.provider_user_id == "google-sub-456")
    )
    accounts = result.scalars().all()
    assert len(accounts) == 1  # not duplicated on repeated logins


async def test_google_login_with_invalid_token_fails(client: AsyncClient, monkeypatch):
    async def _fake_verify(self, id_token: str):
        return None

    monkeypatch.setattr(
        "app.services.auth_service.AuthService._verify_google_id_token", _fake_verify
    )

    resp = await client.post("/api/v1/auth/google", json={"id_token": "bad-token"})
    assert resp.status_code == 401
