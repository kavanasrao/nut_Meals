"""API routes for gift orders."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.gift import GiftOrderCreate, GiftOrderResponse, GiftOrderUpdate
from app.security.auth import Principal
from app.security.rbac import require_customer
from app.services.gift_service import GiftOrderService

router = APIRouter(prefix="/api/v1/gift-orders", tags=["gift-orders"])


@router.post("", response_model=GiftOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_gift_order(
    payload: GiftOrderCreate,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Mark an existing order as a gift and attach recipient/delivery details."""
    service = GiftOrderService(db)
    return await service.create_gift_order(uuid.UUID(principal.customer_id), payload)


@router.get("/{gift_order_id}", response_model=GiftOrderResponse)
async def get_gift_order(
    gift_order_id: uuid.UUID,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Fetch gift metadata (message, recipient, wrap option) for an order."""
    service = GiftOrderService(db)
    return await service.get_gift_order(gift_order_id, uuid.UUID(principal.customer_id))


@router.patch("/{gift_order_id}", response_model=GiftOrderResponse)
async def update_gift_order(
    gift_order_id: uuid.UUID,
    payload: GiftOrderUpdate,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Update gift wrapping, message, or delivery scheduling before fulfillment."""
    service = GiftOrderService(db)
    return await service.update_gift_order(gift_order_id, uuid.UUID(principal.customer_id), payload)
