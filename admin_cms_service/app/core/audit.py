"""
Helper for writing audit log entries. Called by route handlers after any
state-changing admin action (approve return, publish post, export report).
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AdminPrincipal
from app.models.audit import AuditLogEntry


async def record_audit_event(
    db: AsyncSession,
    *,
    actor: AdminPrincipal,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    request_ip: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> AuditLogEntry:
    """
    Persist an audit log entry. Does not commit the session itself --
    callers should commit as part of their own transaction so the audit
    entry and the business-data change land atomically.
    """
    entry = AuditLogEntry(
        actor_admin_id=actor.admin_id,
        actor_role=actor.roles[0].value if actor.roles else "unknown",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_ip=request_ip,
        metadata_json=metadata or {},
    )
    db.add(entry)
    await db.flush()
    return entry
