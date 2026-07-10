"""Helper for writing compliance audit log entries."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def record_audit_event(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    details: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        id=uuid.uuid4(),
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        details=details or {},
    )
    db.add(entry)
    await db.flush()
    return entry
