"""Delivery management routes — proxy to Delivery Service."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.db import get_db
from app.integrations.base_client import DownstreamError, ServiceUnavailableError
from app.integrations.delivery_client import DeliveryServiceClient
from app.models.models import AdminUser
from app.schemas.schemas import DeliveryOptionCreate, DeliveryOptionUpdate
from app.services.audit_service import AuditService

router = APIRouter(prefix="/delivery", tags=["Delivery Management"])


def _delivery_client() -> DeliveryServiceClient:
    return DeliveryServiceClient()


@router.get("/options", summary="List all delivery options (admin view)")
async def list_delivery_options(
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        return await _delivery_client().list_options()
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post(
    "/options",
    status_code=status.HTTP_201_CREATED,
    summary="Add a new delivery option",
)
async def create_delivery_option(
    request: Request,
    body: DeliveryOptionCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        result = await _delivery_client().create_option(body.model_dump())
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="CREATE_DELIVERY_OPTION",
        resource="delivery_option",
        resource_id=(result or {}).get("id"),
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload=body.model_dump(),
        response_status=201,
    )
    return result


@router.patch("/{option_id}", summary="Update a delivery option (enable/disable, ETA)")
async def update_delivery_option(
    request: Request,
    option_id: str,
    body: DeliveryOptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        result = await _delivery_client().update_option(option_id, body.model_dump(exclude_none=True))
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="UPDATE_DELIVERY_OPTION",
        resource="delivery_option",
        resource_id=option_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload=body.model_dump(exclude_none=True),
        response_status=200,
    )
    return result


@router.delete(
    "/{option_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a delivery option (superadmin only)",
)
async def delete_delivery_option(
    request: Request,
    option_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> None:
    try:
        await _delivery_client().delete_option(option_id)
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="DELETE_DELIVERY_OPTION",
        resource="delivery_option",
        resource_id=option_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        response_status=204,
    )
