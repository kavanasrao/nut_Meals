"""Payment Service — business logic layer.

Key design decisions:
  - Never trusts the frontend for payment success — all state changes
    come from verified webhook callbacks.
  - Uses idempotency keys to prevent duplicate payment records.
  - Publishes PAYMENT_SUCCESS / PAYMENT_FAILED events after webhook verification.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.events import EventType
from app.events.publisher import EventPublisher
from app.models.payment import Payment, PaymentStatus
from app.providers.base import WebhookResult
from app.providers.factory import get_payment_provider
from app.schemas.payment import PaymentCreate, PaymentInitResponse

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.provider = get_payment_provider()

    # ------------------------------------------------------------------
    # Create payment — called from POST /payments/create
    # ------------------------------------------------------------------

    async def create_payment(self, data: PaymentCreate) -> PaymentInitResponse:
        """
        Initiate a payment with the configured provider and persist a
        PENDING payment record.

        Uses order_id as the idempotency key — safe to retry if the
        initial request times out.
        """
        idempotency_key = f"{data.order_id}:{self.provider.get_name()}"

        # Return existing payment if already initiated (idempotency)
        existing = await self._get_by_idempotency_key(idempotency_key)
        if existing:
            logger.info("Returning existing payment for idempotency_key=%s", idempotency_key)
            return PaymentInitResponse(
                payment_id=existing.id,
                payment_url=existing.provider_payment_url or "",
                provider=existing.provider,
                status=existing.status,
            )

        # Call provider
        result = await self.provider.create_payment(
            {
                "order_id": data.order_id,
                "amount": str(data.amount),
                "user_id": data.user_id,
                "email": data.email or "",
                "phone": data.phone or "",
                "return_url": data.return_url or "",
            }
        )

        # Persist
        payment = Payment(
            id=uuid.uuid4(),
            order_id=data.order_id,
            user_id=data.user_id,
            provider=result.provider,
            provider_payment_id=result.payment_id,
            provider_payment_url=result.payment_url,
            amount=data.amount,
            currency="INR",
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
        )
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)

        logger.info("Payment %s created for order %s via %s", payment.id, data.order_id, result.provider)

        return PaymentInitResponse(
            payment_id=payment.id,
            payment_url=result.payment_url,
            provider=result.provider,
            status=payment.status,
        )

    # ------------------------------------------------------------------
    # Webhook handler — called from POST /payments/webhook
    # ------------------------------------------------------------------

    async def handle_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict:
        """
        1. Verify signature via provider.
        2. Update payment status in DB.
        3. Emit PAYMENT_SUCCESS or PAYMENT_FAILED event.
        """
        # Verify and parse
        webhook: WebhookResult = await self.provider.verify_webhook(headers, body)
        logger.info("Webhook verified: order=%s status=%s", webhook.order_id, webhook.status)

        # Update DB record
        payment = await self._get_by_order_id(webhook.order_id)
        if payment:
            new_status = (
                PaymentStatus.SUCCESS if webhook.status == "SUCCESS" else PaymentStatus.FAILED
            )
            payment.status = new_status
            payment.provider_payment_id = webhook.payment_id
            payment.webhook_payload = webhook.raw
            await self.db.commit()

        # Publish event — NEVER skip this step
        event_type = (
            EventType.PAYMENT_SUCCESS if webhook.status == "SUCCESS" else EventType.PAYMENT_FAILED
        )
        await EventPublisher.publish(
            event_type,
            {
                "order_id": webhook.order_id,
                "payment_id": webhook.payment_id,
                "provider": webhook.provider,
                "amount": webhook.amount,
                "status": webhook.status,
            },
        )

        return {"received": True, "order_id": webhook.order_id, "status": webhook.status}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_payment_by_order(self, order_id: str) -> Payment | None:
        return await self._get_by_order_id(order_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_by_idempotency_key(self, key: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def _get_by_order_id(self, order_id: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        return result.scalar_one_or_none()
