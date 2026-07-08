"""Audit Log routes.

GET /admin/audit-logs  — paginated, filterable audit trail
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_superadmin
from app.core.db import get_db
from app.models.models import AdminUser, AuditLog
from app.schemas.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "/",
    response_model=list[AuditLogOut],
    summary="List admin audit logs (superadmin only)",
)
async def list_audit_logs(
    admin_email: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    resource: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> list[AuditLogOut]:
    """
    Returns audit log entries in reverse chronological order.

    Filters:
      - admin_email — who performed the action
      - action      — e.g. BLOCK_USER, SWITCH_PAYMENT_PROVIDER
      - resource    — e.g. user, order, meal
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if admin_email:
        query = query.where(AuditLog.admin_email.ilike(f"%{admin_email}%"))
    if action:
        query = query.where(AuditLog.action == action)
    if resource:
        query = query.where(AuditLog.resource == resource)

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()
    return [AuditLogOut.model_validate(e) for e in entries]
