"""Integration routes — surface data owned by other services on the user's
own profile, without the User Service duplicating that data.

GET /api/v1/me/orders    — order history (proxied from Order Service)
GET /api/v1/me/timeline  — CRM customer timeline (proxied from CRM Service)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import require_active_user
from app.integrations.crm_client import crm_client
from app.integrations.orders_client import orders_client
from app.models.user import User

router = APIRouter(tags=["integrations"])


@router.get("/me/orders", summary="My order history (from Order Service)")
async def get_my_orders(
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(require_active_user),
) -> dict:
    orders = await orders_client.get_order_history(str(user.id), limit=limit)
    return {"orders": orders}


@router.get("/me/timeline", summary="My CRM customer timeline (from CRM Service)")
async def get_my_timeline(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_active_user),
) -> dict:
    timeline = await crm_client.get_timeline(str(user.id), limit=limit)
    return {"timeline": timeline}
