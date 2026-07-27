"""Auth Service — business logic for password reset, OTP login, and
Google social login."""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.audit_log import AuditAction, UserAuditLog
from app.models.otp import OtpCode, OtpPurpose
from app.models.password_reset import PasswordResetToken
from app.models.social_account import SocialAccount, SocialProvider
from app.models.user import User, UserRole
from app.tasks.notification_tasks import (
    send_login_alert_task,
    send_otp_task,
    send_password_reset_email_task,
)

logger = logging.getLogger(__name__)


def _hash_token(raw: str) -> str:
    """SHA-256 hash for opaque tokens/OTPs stored at rest (not a password,
    so a fast hash is appropriate — these are high-entropy, short-lived,
    single-use secrets, not user-chosen passwords)."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_otp(length: int) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Forgot / Reset password ─────────────────────────────────────────────

    async def request_password_reset(self, email: str, *, ip_address: str | None = None) -> None:
        """Always succeeds from the caller's perspective (no user enumeration).
        If the email matches an account, issues a token and queues delivery."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            logger.info("Password reset requested for unknown email: %s", email)
            return

        raw_token = secrets.token_urlsafe(48)
        token = PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_TTL_MINUTES),
            requested_ip=ip_address,
        )
        self.db.add(token)
        self.db.add(
            UserAuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                action=AuditAction.PASSWORD_RESET_REQUESTED,
                description="Password reset requested",
                ip_address=ip_address,
            )
        )
        await self.db.commit()

        reset_link = f"{settings.PASSWORD_RESET_BASE_URL}?token={raw_token}"
        send_password_reset_email_task.delay(email=user.email, reset_link=reset_link)

    async def reset_password(self, raw_token: str, new_password: str) -> bool:
        """Consume a reset token and set the new password. Returns False if the
        token is invalid, expired, or already used."""
        token_hash = _hash_token(raw_token)
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        if token is None or token.used_at is not None:
            return False
        if token.expires_at < datetime.now(timezone.utc):
            return False

        user = await self.db.get(User, token.user_id)
        if user is None:
            return False

        user.password_hash = hash_password(new_password)
        token.used_at = datetime.now(timezone.utc)
        self.db.add(
            UserAuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                action=AuditAction.PASSWORD_RESET_COMPLETED,
                description="Password reset completed",
            )
        )
        await self.db.commit()
        return True

    # ── OTP login ────────────────────────────────────────────────────────────

    async def request_otp(self, *, identifier: str, channel: str) -> None:
        """Issue and deliver a fresh OTP for the given identifier/channel.
        A prior unconsumed OTP for the same identifier+purpose is invalidated."""
        now = datetime.now(timezone.utc)

        # Invalidate previous unconsumed OTPs for this identifier to avoid
        # ambiguity about which code is "current".
        result = await self.db.execute(
            select(OtpCode).where(
                OtpCode.identifier == identifier,
                OtpCode.purpose == OtpPurpose.LOGIN,
                OtpCode.consumed_at.is_(None),
            )
        )
        for stale in result.scalars().all():
            stale.consumed_at = now

        code = _generate_otp(settings.OTP_LENGTH)
        otp = OtpCode(
            id=uuid.uuid4(),
            identifier=identifier,
            channel=channel,
            purpose=OtpPurpose.LOGIN,
            code_hash=_hash_token(code),
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            expires_at=now + timedelta(seconds=settings.OTP_TTL_SECONDS),
        )
        self.db.add(otp)
        await self.db.commit()

        send_otp_task.delay(identifier=identifier, channel=channel, code=code)

    async def verify_otp(self, *, identifier: str, code: str) -> User | None:
        """Verify an OTP and return the associated user, creating a new
        (unverified, passwordless) user on first-time OTP login if none
        exists yet. Returns None if the code is invalid/expired/exhausted."""
        result = await self.db.execute(
            select(OtpCode)
            .where(
                OtpCode.identifier == identifier,
                OtpCode.purpose == OtpPurpose.LOGIN,
                OtpCode.consumed_at.is_(None),
            )
            .order_by(OtpCode.created_at.desc())
        )
        otp = result.scalars().first()
        if otp is None:
            return None
        if otp.expires_at < datetime.now(timezone.utc):
            return None
        if otp.attempts >= otp.max_attempts:
            return None

        if _hash_token(code) != otp.code_hash:
            otp.attempts += 1
            await self.db.commit()
            return None

        otp.consumed_at = datetime.now(timezone.utc)

        is_email = "@" in identifier
        user = await self._get_or_create_passwordless_user(
            email=identifier if is_email else None,
            phone=identifier if not is_email else None,
        )
        user.last_login_at = datetime.now(timezone.utc)
        self.db.add(
            UserAuditLog(
                id=uuid.uuid4(),
                user_id=user.id,
                action=AuditAction.OTP_LOGIN,
                description=f"Logged in via OTP ({otp.channel.value})",
            )
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ── Google social login ─────────────────────────────────────────────────

    async def google_login(self, id_token: str) -> User | None:
        """Verify a Google ID token and return the linked/created user.
        Returns None if the token fails verification."""
        claims = await self._verify_google_id_token(id_token)
        if claims is None:
            return None

        provider_user_id = claims.get("sub")
        email = claims.get("email")
        if not provider_user_id or not email:
            return None

        result = await self.db.execute(
            select(SocialAccount).where(
                SocialAccount.provider == SocialProvider.GOOGLE,
                SocialAccount.provider_user_id == provider_user_id,
            )
        )
        social_account = result.scalar_one_or_none()

        if social_account is not None:
            user = await self.db.get(User, social_account.user_id)
        else:
            user = await self._get_or_create_passwordless_user(email=email, phone=None)
            social_account = SocialAccount(
                id=uuid.uuid4(),
                user_id=user.id,
                provider=SocialProvider.GOOGLE,
                provider_user_id=provider_user_id,
                email=email,
            )
            self.db.add(social_account)

        social_account.last_login_at = datetime.now(timezone.utc)
        if user is not None:
            user.last_login_at = datetime.now(timezone.utc)
            self.db.add(
                UserAuditLog(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    action=AuditAction.SOCIAL_LOGIN,
                    description="Logged in via Google",
                )
            )
        await self.db.commit()
        if user is not None:
            await self.db.refresh(user)
        return user

    async def _verify_google_id_token(self, id_token: str) -> dict | None:
        """Verify a Google ID token via Google's tokeninfo endpoint and check
        it was issued for our configured client ID."""
        try:
            async with httpx.AsyncClient(timeout=settings.SERVICE_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    settings.GOOGLE_TOKENINFO_URL, params={"id_token": id_token}
                )
            if response.status_code != 200:
                return None
            claims = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Google token verification request failed: %s", exc)
            return None

        if claims.get("aud") != settings.GOOGLE_CLIENT_ID:
            logger.warning("Google id_token audience mismatch")
            return None
        return claims

    # ── Shared helpers ───────────────────────────────────────────────────────

    async def _get_or_create_passwordless_user(
        self, *, email: str | None, phone: str | None
    ) -> User:
        """Find an existing user by email/phone, or create a new one with an
        unusable random password hash (they authenticate via OTP/social
        only, unless/until they explicitly set a password)."""
        stmt = select(User)
        if email:
            stmt = stmt.where(User.email == email)
        elif phone:
            stmt = stmt.where(User.phone == phone)
        else:
            raise ValueError("email or phone is required")

        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is not None:
            return user

        user = User(
            id=uuid.uuid4(),
            name=(email.split("@")[0] if email else phone) or "New User",
            email=email or f"{phone}@phone.nutmeals.local",
            phone=phone,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.USER,
            is_blocked=False,
            is_verified=True,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def send_login_alert(self, user: User, *, ip_address: str | None) -> None:
        send_login_alert_task.delay(email=user.email, ip_address=ip_address)
