"""Meal / Menu management routes — proxy to Meal Service."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.db import get_db
from app.integrations.base_client import DownstreamError, ServiceUnavailableError
from app.integrations.meal_client import MealServiceClient
from app.models.models import AdminUser
from app.schemas.schemas import MealCreate, MealUpdate
from app.services.audit_service import AuditService

router = APIRouter(prefix="/meals", tags=["Meal Management"])


def _meal_client() -> MealServiceClient:
    return MealServiceClient()


@router.get("/", summary="List all meals")
async def list_meals(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        return await _meal_client().list_meals(limit=limit, offset=offset)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a new meal")
async def create_meal(
    request: Request,
    body: MealCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        result = await _meal_client().create_meal(body.model_dump())
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="CREATE_MEAL",
        resource="meal",
        resource_id=(result or {}).get("id"),
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload={"name": body.name, "price": str(body.price)},
        response_status=201,
    )
    return result


@router.put("/{meal_id}", summary="Update a meal")
async def update_meal(
    request: Request,
    meal_id: str,
    body: MealUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    try:
        result = await _meal_client().update_meal(meal_id, body.model_dump(exclude_none=True))
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="UPDATE_MEAL",
        resource="meal",
        resource_id=meal_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload=body.model_dump(exclude_none=True),
        response_status=200,
    )
    return result


@router.delete(
    "/{meal_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a meal (superadmin only)",
)
async def delete_meal(
    request: Request,
    meal_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> None:
    try:
        await _meal_client().delete_meal(meal_id)
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="DELETE_MEAL",
        resource="meal",
        resource_id=meal_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        response_status=204,
    )
