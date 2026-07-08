"""Order management routes — proxy to Order Service."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.db import get_db
from app.integrations.base_client import DownstreamError, ServiceUnavailableError
from app.integrations.order_client import OrderServiceClient
from app.models.models import AdminUser
from app.schemas.schemas import OrderStatusUpdate
from app.services.audit_service import AuditService

router = APIRouter(prefix="/orders", tags=["Order Management"])


def _order_client() -> OrderServiceClient:
    return OrderServiceClient()


@router.get("/", summary="List all orders (with optional status filter)")
async def list_orders(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    order_status: str | None = Query(default=None, alias="status"),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    client = _order_client()
    try:
        return await client.list_orders(limit=limit, offset=offset, status=order_status)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/{order_id}", summary="Get a specific order")
async def get_order(
    order_id: str,
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    client = _order_client()
    try:
        return await client.get_order(order_id)
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.patch("/{order_id}/status", summary="Update order status")
async def update_order_status(
    request: Request,
    order_id: str,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = Depends(require_admin),
) -> Any:
    client = _order_client()
    try:
        result = await client.update_order_status(order_id, body.status)
    except DownstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    except ServiceUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    await AuditService(db).log(
        admin_id=str(current_admin.id),
        admin_email=current_admin.email,
        admin_role=current_admin.role.value,
        action="UPDATE_ORDER_STATUS",
        resource="order",
        resource_id=order_id,
        http_method=request.method,
        http_path=str(request.url.path),
        ip_address=request.client.host if request.client else None,
        request_payload={"status": body.status},
        response_status=200,
    )
    return result
