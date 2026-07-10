"""Read-only audit log endpoints for compliance review. No write endpoints exist -
audit rows are only ever created internally via app.core.audit.write_audit_log."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import FinanceRole, Principal, require_roles
from app.models.audit import AuditAction, AuditLog

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    action: AuditAction
    actor: str
    entity_type: str
    entity_id: str
    ip_address: str | None
    metadata_json: dict | None
    notes: str | None
    created_at: datetime


@router.get("", response_model=list[AuditLogOut])
async def list_audit_logs(
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: AuditAction | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.ADMIN)),
):
    """Admin-only: audit trail for compliance review / tax audits."""
    stmt = select(AuditLog)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())
