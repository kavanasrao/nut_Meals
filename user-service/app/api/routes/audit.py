"""User audit log routes.

GET /api/v1/audit/me            — my own audit trail
GET /api/v1/audit/{user_id}     — a user's audit trail (admin only)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_active_user
from app.core.db import get_db
from app.core.rbac import require_admin
from app.models.user import User
from app.schemas.audit import AuditLogListResponse, AuditLogOut
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/me", response_model=AuditLogListResponse, summary="My audit trail")
async def get_my_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> AuditLogListResponse:
    svc = AuditService(db)
    logs, total = await svc.list_for_user(user.id, limit=limit, offset=offset)
    return AuditLogListResponse(
        logs=[AuditLogOut.model_validate(l) for l in logs], total=total, limit=limit, offset=offset
    )


@router.get(
    "/{user_id}",
    response_model=AuditLogListResponse,
    summary="A user's audit trail (admin only)",
)
async def get_user_audit_logs(
    user_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AuditLogListResponse:
    svc = AuditService(db)
    logs, total = await svc.list_for_user(user_id, limit=limit, offset=offset)
    return AuditLogListResponse(
        logs=[AuditLogOut.model_validate(l) for l in logs], total=total, limit=limit, offset=offset
    )
