"""User Service — business logic layer."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import (
    ChangePasswordRequest,
    RegisterRequest,
    UserProfileUpdate,
    UserStatsResponse,
)

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "user:"


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Registration ──────────────────────────────────────────────────────────

    async def register(self, data: RegisterRequest) -> User:
        """Create a new user. Raises ValueError on duplicate email/phone."""
        # Check email uniqueness
        result = await self.db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
            raise ValueError(f"Email '{data.email}' is already registered")

        if data.phone:
            result = await self.db.execute(select(User).where(User.phone == data.phone))
            if result.scalar_one_or_none():
                raise ValueError(f"Phone '{data.phone}' is already registered")

        user = User(
            id=uuid.uuid4(),
            name=data.name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            role=UserRole.USER,
            is_blocked=False,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info("User registered: %s (id=%s)", user.email, user.id)
        return user

    # ── Authentication ────────────────────────────────────────────────────────

    async def authenticate(self, email: str, password: str) -> User | None:
        """Return User if credentials are valid, else None."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            return None
        # Record last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        return user

    # ── Profile ───────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch user by UUID — checks Redis cache first."""
        redis = await get_redis()
        cache_key = f"{_CACHE_PREFIX}{user_id}"

        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            # Re-hydrate ORM object from cache dict
            result = await self.db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            return None

        result = await self.db.execute(select(User).where(User.id == uid))
        user = result.scalar_one_or_none()

        if user:
            # Cache ID for TTL to reduce DB load on high-traffic reads
            await redis.setex(cache_key, settings.USER_CACHE_TTL, "1")

        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        if data.name is not None:
            user.name = data.name
        if data.phone is not None:
            user.phone = data.phone
        if data.bio is not None:
            user.bio = data.bio
        if data.profile_picture is not None:
            user.profile_picture = data.profile_picture
        await self.db.commit()
        await self.db.refresh(user)
        await self._invalidate_cache(str(user.id))
        return user

    async def change_password(self, user: User, data: ChangePasswordRequest) -> bool:
        if not verify_password(data.current_password, user.password_hash):
            return False
        user.password_hash = hash_password(data.new_password)
        await self.db.commit()
        return True

    # ── Admin actions ─────────────────────────────────────────────────────────

    async def block(self, user_id: str) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_blocked = True
        await self.db.commit()
        await self.db.refresh(user)
        await self._invalidate_cache(user_id)
        logger.info("User blocked: %s", user_id)
        return user

    async def unblock(self, user_id: str) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        user.is_blocked = False
        await self.db.commit()
        await self.db.refresh(user)
        await self._invalidate_cache(user_id)
        logger.info("User unblocked: %s", user_id)
        return user

    # ── Listing / stats ───────────────────────────────────────────────────────

    async def list_users(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[User], int]:
        count_result = await self.db.execute(select(func.count()).select_from(User))
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_stats(self) -> UserStatsResponse:
        total_r = await self.db.execute(select(func.count()).select_from(User))
        total = total_r.scalar_one()

        blocked_r = await self.db.execute(
            select(func.count()).select_from(User).where(User.is_blocked == True)
        )
        blocked = blocked_r.scalar_one()

        return UserStatsResponse(total=total, active=total - blocked, blocked=blocked)

    # ── Cache ─────────────────────────────────────────────────────────────────

    async def _invalidate_cache(self, user_id: str) -> None:
        redis = await get_redis()
        await redis.delete(f"{_CACHE_PREFIX}{user_id}")
