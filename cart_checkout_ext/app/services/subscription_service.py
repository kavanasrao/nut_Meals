"""Business logic for recurring meal subscriptions."""
import uuid
from datetime import datetime, timedelta, timezone

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionFrequency, SubscriptionStatus
from app.schemas.subscription import SubscriptionCreate
from app.security.audit import log_audit_event


def compute_next_renewal(start: datetime, frequency: SubscriptionFrequency) -> datetime:
    if frequency == SubscriptionFrequency.WEEKLY:
        return start + timedelta(weeks=1)
    return start + relativedelta(months=1)


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_subscription(self, customer_id: uuid.UUID, payload: SubscriptionCreate) -> Subscription:
        start = payload.start_date or datetime.now(timezone.utc)
        subscription = Subscription(
            customer_id=customer_id,
            plan_id=payload.plan_id,
            plan_snapshot=payload.plan_snapshot,
            frequency=payload.frequency,
            price_amount=payload.price_amount,
            currency=payload.currency,
            payment_method_token=payload.payment_method_token,
            shipping_address_id=payload.shipping_address_id,
            next_renewal_date=compute_next_renewal(start, payload.frequency),
            status=SubscriptionStatus.ACTIVE,
        )
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)

        log_audit_event(
            actor_id=str(customer_id),
            action="subscription.create",
            resource=f"subscription:{subscription.id}",
        )
        return subscription

    async def _get_owned_subscription(self, subscription_id: uuid.UUID, customer_id: uuid.UUID) -> Subscription:
        result = await self.db.execute(select(Subscription).where(Subscription.id == subscription_id))
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
        if str(subscription.customer_id) != str(customer_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your subscription")
        return subscription

    async def get_subscription(self, subscription_id: uuid.UUID, customer_id: uuid.UUID) -> Subscription:
        return await self._get_owned_subscription(subscription_id, customer_id)

    async def list_subscriptions(self, customer_id: uuid.UUID) -> list[Subscription]:
        result = await self.db.execute(select(Subscription).where(Subscription.customer_id == customer_id))
        return list(result.scalars().all())

    async def pause_subscription(
        self, subscription_id: uuid.UUID, customer_id: uuid.UUID, reason: str | None
    ) -> Subscription:
        subscription = await self._get_owned_subscription(subscription_id, customer_id)
        if subscription.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause a subscription in status={subscription.status.value}",
            )
        subscription.status = SubscriptionStatus.PAUSED
        subscription.paused_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(subscription)

        log_audit_event(
            actor_id=str(customer_id),
            action="subscription.pause",
            resource=f"subscription:{subscription.id}",
            detail=reason,
        )
        return subscription

    async def resume_subscription(self, subscription_id: uuid.UUID, customer_id: uuid.UUID) -> Subscription:
        subscription = await self._get_owned_subscription(subscription_id, customer_id)
        if subscription.status != SubscriptionStatus.PAUSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume a subscription in status={subscription.status.value}",
            )
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.paused_at = None
        subscription.next_renewal_date = compute_next_renewal(
            datetime.now(timezone.utc), subscription.frequency
        )
        await self.db.commit()
        await self.db.refresh(subscription)

        log_audit_event(
            actor_id=str(customer_id),
            action="subscription.resume",
            resource=f"subscription:{subscription.id}",
        )
        return subscription

    async def cancel_subscription(
        self, subscription_id: uuid.UUID, customer_id: uuid.UUID, reason: str | None
    ) -> Subscription:
        subscription = await self._get_owned_subscription(subscription_id, customer_id)
        if subscription.status == SubscriptionStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already cancelled")
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(timezone.utc)
        subscription.cancellation_reason = reason
        await self.db.commit()
        await self.db.refresh(subscription)

        log_audit_event(
            actor_id=str(customer_id),
            action="subscription.cancel",
            resource=f"subscription:{subscription.id}",
            detail=reason,
        )
        return subscription
