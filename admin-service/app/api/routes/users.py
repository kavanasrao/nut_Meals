"""User management routes — proxy to User Service."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.dependencies import require_admin, require_superadmin
from app.core.db import get_db
from app.integrations.base_client import DownstreamError, ServiceUnavailableError
from app.integrations.user_client import UserServiceClient
from app.models.models import AdminUser
from app.services.audit_service import AuditService
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["User Management"])


def _user_client() -> UserServiceClient:
    return UserServiceClient()


@router.get("/", summary="List all end-users")
async def list_users(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    client = _user_client()
    try:
        return await client.list_users(limit=limit, offset=offset)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/{user_id}", summary="Get a specific user")
async def get_user(
    user_id: str,
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    client = _user_client()
    try:
        return await client.get_user(user_id)
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.patch("/{user_id}/block", summary="Block a user")
async def block_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    client = _user_client()
    try:
        result = await client.block_user(user_id)
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="BLOCK_USER",
        resource="user",
        resource_id=user_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        response_status=200,
    )
    return result


@router.patch("/{user_id}/unblock", summary="Unblock a user")
async def unblock_user(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    client = _user_client()
    try:
        result = await client.unblock_user(user_id)
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="UNBLOCK_USER",
        resource="user",
        resource_id=user_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        response_status=200,
    )
    return result
