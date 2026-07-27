"""Preference Service — customer preferences (language, dark mode, marketing
opt-in, notification channels). One row per user, created lazily."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preference import UserPreference
from app.schemas.preference import PreferenceUpdate


class PreferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, user_id: uuid.UUID) -> UserPreference:
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        pref = result.scalar_one_or_none()
        if pref is not None:
            return pref

        pref = UserPreference(id=uuid.uuid4(), user_id=user_id)
        self.db.add(pref)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    async def update(self, user_id: uuid.UUID, data: PreferenceUpdate) -> UserPreference:
        pref = await self.get_or_create(user_id)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(pref, field, value)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref
