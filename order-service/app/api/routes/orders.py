"""Order Service — REST API routes.

Endpoints:
  POST   /api/v1/orders            Create a new order
  GET    /api/v1/orders/{order_id} Retrieve a single order
  GET    /api/v1/orders/user/{uid} List all orders for a user
  PATCH  /api/v1/orders/{order_id}/status  Update order status (internal)
  POST   /api/v1/orders/{order_id}/cancel  Cancel an order
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def _serialize(order) -> dict:
    """Convert ORM Order to a dict usable by OrderOut."""
    return {
        **{c.key: getattr(order, c.key) for c in order.__mapper__.columns},
        "items": list(order.items),
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
    }


@router.post(
    "/",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    svc = OrderService(db)
    order = await svc.create_order(body)
    return OrderOut.model_validate(_serialize(order))


@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Get order by ID",
)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    svc = OrderService(db)
    order = await svc.get_order(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderOut.model_validate(_serialize(order))


@router.get(
    "/user/{user_id}",
    response_model=list[OrderOut],
    summary="List all orders for a user",
)
async def list_user_orders(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[OrderOut]:
    svc = OrderService(db)
    orders = await svc.list_orders_for_user(user_id)
    return [OrderOut.model_validate(_serialize(o)) for o in orders]


@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="Update order status (internal use only)",
)
async def update_order_status(
    order_id: str,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    svc = OrderService(db)
    order = await svc.update_status(order_id, body)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderOut.model_validate(_serialize(order))


@router.post(
    "/{order_id}/cancel",
    response_model=OrderOut,
    summary="Cancel an order",
)
async def cancel_order(
    order_id: str,
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    svc = OrderService(db)
    order = await svc.cancel_order(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderOut.model_validate(_serialize(order))
