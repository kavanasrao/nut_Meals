"""
API routes for Returns Management: list/inspect returns, approve/reject
decisions, and resolution tracking (tiers A-C).
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.security import AdminPrincipal, require_roles
from app.database import get_db
from app.models.common import AdminRole, ReturnStatus
from app.schemas.returns import (
    ReturnDecisionRequest,
    ReturnRequestListResponse,
    ReturnRequestResponse,
)
from app.services import returns_service
from app.services.logistics_client import LogisticsServiceClient, get_logistics_client

router = APIRouter(prefix="/api/v1/returns", tags=["returns"])

_DECISION_ROLES = (AdminRole.SUPER_ADMIN, AdminRole.SUPPORT_ADMIN)
_READ_ROLES = (AdminRole.SUPER_ADMIN, AdminRole.SUPPORT_ADMIN, AdminRole.ANALYTICS_VIEWER)


@router.get("", response_model=ReturnRequestListResponse)
async def list_returns(
    status_filter: Optional[ReturnStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_READ_ROLES)),
) -> ReturnRequestListResponse:
    items, total = await returns_service.list_return_requests(
        db, status_filter=status_filter, page=page, page_size=page_size
    )
    return ReturnRequestListResponse(
        items=[ReturnRequestResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{return_id}", response_model=ReturnRequestResponse)
async def get_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_READ_ROLES)),
) -> ReturnRequestResponse:
    ret = await returns_service.get_return_request(db, return_id)
    return ReturnRequestResponse.model_validate(ret)


@router.post("/{return_id}/approve", response_model=ReturnRequestResponse)
async def approve_return(
    return_id: uuid.UUID,
    payload: ReturnDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_DECISION_ROLES)),
    logistics_client: LogisticsServiceClient = Depends(get_logistics_client),
) -> ReturnRequestResponse:
    """Approve a return request, set its resolution tier, and (if restock is
    required) trigger a reverse-logistics pickup via the Logistics service."""
    ret = await returns_service.approve_return(
        db,
        return_id=return_id,
        decision=payload,
        actor_admin_id=admin.admin_id,
        logistics_client=logistics_client,
    )
    await record_audit_event(
        db,
        actor=admin,
        action="return.approve",
        resource_type="return_request",
        resource_id=str(return_id),
        request_ip=request.client.host if request.client else None,
        metadata={"tier": payload.tier.value, "refund_amount": str(payload.refund_amount)},
    )
    await db.commit()
    return ReturnRequestResponse.model_validate(ret)


@router.post("/{return_id}/reject", response_model=ReturnRequestResponse)
async def reject_return(
    return_id: uuid.UUID,
    payload: ReturnDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_DECISION_ROLES)),
) -> ReturnRequestResponse:
    ret = await returns_service.reject_return(
        db, return_id=return_id, decision=payload, actor_admin_id=admin.admin_id
    )
    await record_audit_event(
        db,
        actor=admin,
        action="return.reject",
        resource_type="return_request",
        resource_id=str(return_id),
        request_ip=request.client.host if request.client else None,
        metadata={"reason": payload.resolution_notes},
    )
    await db.commit()
    return ReturnRequestResponse.model_validate(ret)


@router.post("/{return_id}/resolve", response_model=ReturnRequestResponse)
async def resolve_return(
    return_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_DECISION_ROLES)),
) -> ReturnRequestResponse:
    """Mark an approved return as fully resolved (refund issued / item restocked)."""
    ret = await returns_service.resolve_return(db, return_id=return_id, actor_admin_id=admin.admin_id)
    await record_audit_event(
        db,
        actor=admin,
        action="return.resolve",
        resource_type="return_request",
        resource_id=str(return_id),
        request_ip=request.client.host if request.client else None,
    )
    await db.commit()
    return ReturnRequestResponse.model_validate(ret)
