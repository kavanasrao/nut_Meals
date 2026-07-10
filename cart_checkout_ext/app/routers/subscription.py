"""API routes for recurring meal subscription lifecycle management."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.subscription import (
    SubscriptionCancelRequest,
    SubscriptionCreate,
    SubscriptionPauseRequest,
    SubscriptionResponse,
)
from app.security.auth import Principal
from app.security.rbac import require_customer
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: SubscriptionCreate,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Create a new recurring meal subscription (weekly or monthly)."""
    service = SubscriptionService(db)
    return await service.create_subscription(uuid.UUID(principal.customer_id), payload)


@router.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """List all subscriptions belonging to the authenticated customer."""
    service = SubscriptionService(db)
    return await service.list_subscriptions(uuid.UUID(principal.customer_id))


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: uuid.UUID,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single subscription's current state."""
    service = SubscriptionService(db)
    return await service.get_subscription(subscription_id, uuid.UUID(principal.customer_id))


@router.post("/{subscription_id}/pause", response_model=SubscriptionResponse)
async def pause_subscription(
    subscription_id: uuid.UUID,
    payload: SubscriptionPauseRequest,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Pause an active subscription; billing stops until resumed."""
    service = SubscriptionService(db)
    return await service.pause_subscription(subscription_id, uuid.UUID(principal.customer_id), payload.reason)


@router.post("/{subscription_id}/resume", response_model=SubscriptionResponse)
async def resume_subscription(
    subscription_id: uuid.UUID,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Resume a paused subscription and schedule its next renewal."""
    service = SubscriptionService(db)
    return await service.resume_subscription(subscription_id, uuid.UUID(principal.customer_id))


@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: uuid.UUID,
    payload: SubscriptionCancelRequest,
    principal: Principal = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a subscription permanently. No further renewals will be billed."""
    service = SubscriptionService(db)
    return await service.cancel_subscription(
        subscription_id, uuid.UUID(principal.customer_id), payload.reason
    )
