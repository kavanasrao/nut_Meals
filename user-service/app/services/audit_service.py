"""Audit Service — write and query User Service audit logs.

Every profile change, address change, preference change, and auth event
funnels through `record()` so there's a single, consistent append-only
trail per user. This is a User-Service-local audit log; account/security
events that need platform-wide visibility are additionally mirrored to
security-service's central audit log (see `app.integrations` if/when that
sync is wired in — kept separate so a security-service outage never blocks
a profile update here).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, UserAuditLog


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        user_id: Optional[uuid.UUID],
        action: AuditAction,
        description: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        extra_data: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> UserAuditLog:
        log = UserAuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data,
        )
        self.db.add(log)
        if commit:
            await self.db.commit()
            await self.db.refresh(log)
        return log

    async def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[UserAuditLog], int]:
        count_r = await self.db.execute(
            select(func.count()).select_from(UserAuditLog).where(UserAuditLog.user_id == user_id)
        )
        total = count_r.scalar_one()

        result = await self.db.execute(
            select(UserAuditLog)
            .where(UserAuditLog.user_id == user_id)
            .order_by(UserAuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total
