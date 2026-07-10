"""Central helper for writing append-only audit log entries."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditAction, AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    action: AuditAction,
    actor: str,
    entity_type: str,
    entity_id: str,
    ip_address: str | None = None,
    metadata: dict | None = None,
    notes: str | None = None,
    flush: bool = True,
) -> AuditLog:
    """
    Writes an audit row within the *current* transaction so that the audit
    trail and the underlying financial mutation either both commit or both
    roll back together (no orphaned audit entries, no un-audited mutations).
    """
    log = AuditLog(
        action=action,
        actor=actor,
        entity_type=entity_type,
        entity_id=str(entity_id),
        ip_address=ip_address,
        metadata_json=metadata,
        notes=notes,
    )
    db.add(log)
    if flush:
        await db.flush()
    return log
