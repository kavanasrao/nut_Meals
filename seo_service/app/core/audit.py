"""Helper for writing immutable audit log entries for mutating actions."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models.ai_discovery import AuditLogEntry


async def record_audit_event(
    db: AsyncSession,
    *,
    user: CurrentUser,
    action: str,
    target_type: str,
    target_id: str | None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit trail row. Never raises to avoid blocking the primary action;
    logs internally on failure instead, since audit-log writes should not take down
    a legitimate SEO admin operation."""
    entry = AuditLogEntry(
        actor_subject=user.subject,
        actor_role=user.role.value,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_state=before_state,
        after_state=after_state,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
