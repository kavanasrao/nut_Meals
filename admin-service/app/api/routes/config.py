"""System Configuration routes.

GET   /admin/config          — list all config entries
PATCH /admin/config          — upsert a config entry
DELETE /admin/config/{key}   — delete a non-protected config entry (superadmin)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, require_superadmin
from app.core.db import get_db
from app.models.models import AdminUser
from app.schemas.schemas import ConfigEntry, ConfigOut, ConfigUpdate
from app.services.audit_service import AuditService
from app.services.config_service import ConfigService

router = APIRouter(prefix="/config", tags=["System Configuration"])


@router.get(
    "/",
    response_model=list[ConfigOut],
    summary="List all system config entries",
)
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> list[ConfigOut]:
    svc = ConfigService(db)
    entries = await svc.get_all()
    return [ConfigOut.model_validate(e) for e in entries]


@router.patch(
    "/",
    response_model=ConfigOut,
    summary="Create or update a config entry",
)
async def upsert_config(
    request: Request,
    body: ConfigEntry,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> ConfigOut:
    svc = ConfigService(db)
    entry = await svc.upsert(
        body.key,
        body.value,
        description=body.description,
        updated_by=current_admin.email,
    )

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="UPSERT_CONFIG",
        resource="system_config",
        resource_id=body.key,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload={"key": body.key, "value": body.value},
        response_status=200,
    )
    return ConfigOut.model_validate(entry)


@router.delete(
    "/{key}",
    status_code=status.HTTP_200_OK,
    summary="Delete a config entry (superadmin only)",
)
async def delete_config(
    request: Request,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_superadmin),
) -> None:
    svc = ConfigService(db)
    try:
        deleted = await svc.delete(key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config key not found")

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="DELETE_CONFIG",
        resource="system_config",
        resource_id=key,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        response_status=204,
    )
