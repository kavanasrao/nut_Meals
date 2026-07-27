"""Tests for the OTP login flow (request + verify)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OtpCode
from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_request_otp_sends_via_configured_channel(
    client: AsyncClient, stub_notification_tasks
):
    resp = await client.post(
        "/api/v1/auth/otp/request", json={"channel": "email", "email": "otp-user@example.com"}
    )
    assert resp.status_code == 200
    assert len(stub_notification_tasks["otp"]) == 1
    assert stub_notification_tasks["otp"][0]["identifier"] == "otp-user@example.com"
    assert stub_notification_tasks["otp"][0]["channel"] == "email"


async def test_verify_otp_with_correct_code_creates_user_and_returns_tokens(
    client: AsyncClient, db_session: AsyncSession, stub_notification_tasks
):
    identifier = "new-otp-user@example.com"
    await client.post("/api/v1/auth/otp/request", json={"channel": "email", "email": identifier})

    # Recover the raw code deterministically by overwriting the stored hash
    # with a known code, so the test doesn't depend on the random code
    # actually delivered (which is stubbed out via stub_notification_tasks).
    from app.services.auth_service import _hash_token

    result = await db_session.execute(
        select(OtpCode).where(OtpCode.identifier == identifier).order_by(OtpCode.created_at.desc())
    )
    otp = result.scalars().first()
    known_code = "123456"
    otp.code_hash = _hash_token(known_code)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"channel": "email", "email": identifier, "code": known_code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body

    result = await db_session.execute(select(User).where(User.email == identifier))
    created_user = result.scalar_one_or_none()
    assert created_user is not None
    assert created_user.is_verified is True


async def test_verify_otp_with_wrong_code_fails(client: AsyncClient, db_session: AsyncSession):
    identifier = "wrong-code-user@example.com"
    await client.post("/api/v1/auth/otp/request", json={"channel": "email", "email": identifier})

    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"channel": "email", "email": identifier, "code": "000000"},
    )
    assert resp.status_code == 400


async def test_verify_otp_without_prior_request_fails(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/otp/verify",
        json={"channel": "email", "email": "never-requested@example.com", "code": "123456"},
    )
    assert resp.status_code == 400


async def test_otp_exhausts_after_max_attempts(client: AsyncClient, db_session: AsyncSession):
    identifier = "exhaust-user@example.com"
    await client.post("/api/v1/auth/otp/request", json={"channel": "email", "email": identifier})

    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/otp/verify",
            json={"channel": "email", "email": identifier, "code": "999999"},
        )
        assert resp.status_code == 400

    result = await db_session.execute(
        select(OtpCode).where(OtpCode.identifier == identifier).order_by(OtpCode.created_at.desc())
    )
    otp = result.scalars().first()
    assert otp.attempts >= otp.max_attempts
