"""System Config service — CRUD on the system_config table.

This is the single source of truth for all runtime configuration.
Other services poll their own config endpoint or receive events
when a config key changes.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import SystemConfig

logger = logging.getLogger(__name__)

# Keys that are forbidden from being deleted (must always exist)
PROTECTED_KEYS = {"payment_provider", "whatsapp_provider"}


class ConfigService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all(self) -> list[SystemConfig]:
        result = await self.db.execute(select(SystemConfig).order_by(SystemConfig.key))
        return list(result.scalars().all())

    async def get(self, key: str) -> SystemConfig | None:
        result = await self.db.execute(select(SystemConfig).where(SystemConfig.key == key))
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default: str = "") -> str:
        entry = await self.get(key)
        return entry.value if entry else default

    async def upsert(
        self,
        key: str,
        value: str,
        *,
        description: str | None = None,
        updated_by: str | None = None,
    ) -> SystemConfig:
        """Create or update a config entry atomically."""
        entry = await self.get(key)
        if entry:
            entry.value = value
            if description is not None:
                entry.description = description
            entry.updated_by = updated_by
        else:
            import uuid
            entry = SystemConfig(
                id=uuid.uuid4(),
                key=key,
                value=value,
                description=description,
                updated_by=updated_by,
            )
            self.db.add(entry)

        await self.db.commit()
        await self.db.refresh(entry)
        logger.info("Config updated: %s → %s (by %s)", key, value, updated_by)
        return entry

    async def delete(self, key: str) -> bool:
        if key in PROTECTED_KEYS:
            raise ValueError(f"Config key '{key}' is protected and cannot be deleted")
        entry = await self.get(key)
        if not entry:
            return False
        await self.db.delete(entry)
        await self.db.commit()
        return True
