"""Helper for writing security-relevant audit log entries."""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    actor_id: Optional[str],
    actor_role: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Persist an audit record. Caller is responsible for committing the session
    (typically as part of the same transaction as the mutation being audited)."""
    entry = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
