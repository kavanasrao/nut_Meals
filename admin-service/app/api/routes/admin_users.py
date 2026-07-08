"""Admin User Management routes (superadmin only for creation/promotion)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_superadmin
from app.core.db import get_db
from app.models.models import AdminUser
from app.schemas.schemas import AdminUserCreate, AdminUserOut, AdminUserUpdate
from app.services.admin_user_service import AdminUserService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin-users", tags=["Admin User Management"])


@router.post(
    "/",
    response_model=AdminUserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new admin user (superadmin only)",
)
async def create_admin_user(
    request: Request,
    body: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> AdminUserOut:
    svc = AdminUserService(db)
    try:
        admin = await svc.create(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="CREATE_ADMIN_USER",
        resource="admin_user",
        resource_id=str(admin.id),
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload={"email": body.email, "role": body.role.value},
        response_status=201,
    )
    return AdminUserOut.model_validate(admin)


@router.get(
    "/",
    response_model=list[AdminUserOut],
    summary="List all admin users (superadmin only)",
)
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> list[AdminUserOut]:
    svc = AdminUserService(db)
    admins = await svc.list_admins()
    return [AdminUserOut.model_validate(a) for a in admins]


@router.patch(
    "/{admin_id}",
    response_model=AdminUserOut,
    summary="Update an admin user (superadmin only)",
)
async def update_admin_user(
    request: Request,
    admin_id: str,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> AdminUserOut:
    svc = AdminUserService(db)
    admin = await svc.update(admin_id, body)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="UPDATE_ADMIN_USER",
        resource="admin_user",
        resource_id=admin_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload=body.model_dump(exclude_none=True),
        response_status=200,
    )
    return AdminUserOut.model_validate(admin)
