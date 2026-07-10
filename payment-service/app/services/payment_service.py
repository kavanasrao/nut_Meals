"""
Payment Service - Business Logic Layer

Responsibilities:
- Payment creation
- Idempotency
- Gateway failover
- Webhook processing
- Refund orchestration
- Settlement reconciliation
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.events import EventType
from app.events.publisher import EventPublisher

from app.models.payment import (
    Payment,
    PaymentStatus,
)

from app.providers.base import (
    WebhookResult,
)

from app.providers.factory import (
    get_payment_provider,
    get_fallback_providers,
)

from app.schemas.payment import (
    PaymentCreate,
    PaymentInitResponse,
)

logger = logging.getLogger(__name__)


class PaymentService:

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:

        self.db = db

        self.provider = get_payment_provider()

        self.fallback_providers = get_fallback_providers()

    # ==========================================================
    # CREATE PAYMENT
    # ==========================================================

    async def create_payment(
        self,
        data: PaymentCreate,
    ) -> PaymentInitResponse:

        idempotency_key = (
            f"{data.order_id}:{self.provider.get_name()}"
        )

        existing = await self._get_by_idempotency_key(
            idempotency_key
        )

        if existing:

            logger.info(
                "Returning existing payment %s",
                existing.id,
            )

            return PaymentInitResponse(
                payment_id=existing.id,
                payment_url=existing.provider_payment_url or "",
                provider=existing.provider,
                status=existing.status,
            )

        payment_request = {
            "order_id": data.order_id,
            "amount": str(data.amount),
            "user_id": data.user_id,
            "email": data.email or "",
            "phone": data.phone or "",
            "return_url": data.return_url or "",
        }

        provider_used = self.provider

        # -------------------------------------------------------
        # Primary Gateway
        # -------------------------------------------------------

        try:

            result = await provider_used.create_payment(
                payment_request
            )

        except Exception as primary_error:

            logger.exception(
                "Primary gateway %s failed.",
                provider_used.get_name(),
            )

            result = None

            # ---------------------------------------------------
            # Fallback Gateways
            # ---------------------------------------------------

            for fallback in self.fallback_providers:

                try:

                    logger.info(
                        "Trying fallback provider %s",
                        fallback.get_name(),
                    )

                    result = await fallback.create_payment(
                        payment_request
                    )

                    provider_used = fallback

                    logger.info(
                        "Fallback provider %s succeeded.",
                        fallback.get_name(),
                    )

                    break

                except Exception:

                    logger.exception(
                        "Fallback provider %s failed.",
                        fallback.get_name(),
                    )

            if result is None:

                raise RuntimeError(
                    "All payment providers failed."
                ) from primary_error

        payment = Payment(
            id=uuid.uuid4(),
            order_id=data.order_id,
            user_id=data.user_id,
            provider=provider_used.get_name(),
            provider_payment_id=result.payment_id,
            provider_payment_url=result.payment_url,
            amount=data.amount,
            currency="INR",
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key,
            gateway_response=result.raw,
        )

        self.db.add(payment)

        await self.db.commit()

        await self.db.refresh(payment)

        await EventPublisher.publish(
            EventType.PAYMENT_CREATED,
            {
                "payment_id": str(payment.id),
                "order_id": payment.order_id,
                "provider": payment.provider,
                "amount": str(payment.amount),
            },
        )

        logger.info(
            "Payment %s created successfully using %s",
            payment.id,
            payment.provider,
        )

        return PaymentInitResponse(
            payment_id=payment.id,
            payment_url=result.payment_url,
            provider=payment.provider,
            status=payment.status,
        )
    
        # ==========================================================
    # WEBHOOK HANDLER
    # ==========================================================

    async def handle_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> dict:

        webhook: WebhookResult = await self.provider.verify_webhook(
            headers,
            body,
        )

        logger.info(
            "Webhook received for order %s",
            webhook.order_id,
        )

        payment = await self._get_by_order_id(
            webhook.order_id
        )

        if payment is None:

            logger.warning(
                "Payment not found for order %s",
                webhook.order_id,
            )

            return {
                "received": False,
                "reason": "payment_not_found",
            }

        payment.provider_payment_id = webhook.payment_id
        payment.webhook_payload = webhook.raw

        if webhook.status == "SUCCESS":

            payment.status = PaymentStatus.SUCCESS

            await EventPublisher.publish(
                EventType.PAYMENT_SUCCESS,
                {
                    "payment_id": str(payment.id),
                    "order_id": payment.order_id,
                    "provider": webhook.provider,
                    "amount": str(webhook.amount),
                },
            )

        elif webhook.status == "FAILED":

            payment.status = PaymentStatus.FAILED

            await EventPublisher.publish(
                EventType.PAYMENT_FAILED,
                {
                    "payment_id": str(payment.id),
                    "order_id": payment.order_id,
                    "provider": webhook.provider,
                },
            )

        else:

            payment.status = PaymentStatus.PENDING

            await EventPublisher.publish(
                EventType.PAYMENT_PENDING,
                {
                    "payment_id": str(payment.id),
                    "order_id": payment.order_id,
                },
            )

        await self.db.commit()

        logger.info(
            "Payment %s updated to %s",
            payment.id,
            payment.status.value,
        )

        return {
            "received": True,
            "order_id": webhook.order_id,
            "status": webhook.status,
        }

    # ==========================================================
    # REFUNDS
    # ==========================================================

    async def create_refund(
        self,
        payment: Payment,
        amount,
        reason: str | None = None,
    ):

        logger.info(
            "Initiating refund for payment %s",
            payment.id,
        )

        refund = await self.provider.refund(
            payment.provider_payment_id,
            amount,
            reason,
        )

        return refund

    # ==========================================================
    # SETTLEMENT IMPORT
    # ==========================================================

    async def import_settlements(self):

        settlements = await self.provider.fetch_settlements()

        logger.info(
            "Fetched %d settlements",
            len(settlements),
        )

        return settlements

    # ==========================================================
    # RECONCILIATION
    # ==========================================================

    async def reconcile_settlement(self):

        settlements = await self.import_settlements()

        reconciled = 0

        mismatches = 0

        for settlement in settlements:

            payment = await self._get_by_provider_payment_id(
                settlement.settlement_reference,
            )

            if payment is None:

                mismatches += 1

                await EventPublisher.publish(
                    EventType.SETTLEMENT_MISMATCH,
                    {
                        "reference": settlement.settlement_reference,
                    },
                )

                continue

            reconciled += 1

            await EventPublisher.publish(
                EventType.SETTLEMENT_RECONCILED,
                {
                    "payment_id": str(payment.id),
                    "reference": settlement.settlement_reference,
                },
            )

        logger.info(
            "Settlement reconciliation completed. reconciled=%d mismatches=%d",
            reconciled,
            mismatches,
        )

        return {
            "reconciled": reconciled,
            "mismatches": mismatches,
        }
    
        # ==========================================================
    # PUBLIC QUERIES
    # ==========================================================

    async def get_payment(
        self,
        payment_id: str,
    ) -> Payment | None:
        """
        Fetch payment by primary key.
        """

        return await self.db.get(
            Payment,
            payment_id,
        )

    async def get_payment_by_order(
        self,
        order_id: str,
    ) -> Payment | None:
        """
        Fetch payment using order id.
        """

        return await self._get_by_order_id(
            order_id
        )

    async def list_payments(
        self,
        limit: int = 100,
    ) -> list[Payment]:
        """
        List latest payments.
        """

        result = await self.db.execute(
            select(Payment)
            .order_by(
                Payment.created_at.desc()
            )
            .limit(limit)
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # INTERNAL HELPERS
    # ==========================================================

    async def _get_by_idempotency_key(
        self,
        key: str,
    ) -> Payment | None:

        result = await self.db.execute(
            select(Payment).where(
                Payment.idempotency_key == key
            )
        )

        return result.scalar_one_or_none()

    async def _get_by_order_id(
        self,
        order_id: str,
    ) -> Payment | None:

        result = await self.db.execute(
            select(Payment).where(
                Payment.order_id == order_id
            )
        )

        return result.scalar_one_or_none()

    async def _get_by_provider_payment_id(
        self,
        provider_payment_id: str,
    ) -> Payment | None:

        result = await self.db.execute(
            select(Payment).where(
                Payment.provider_payment_id
                == provider_payment_id
            )
        )

        return result.scalar_one_or_none()

    async def payment_exists(
        self,
        order_id: str,
    ) -> bool:
        """
        Returns True if a payment already exists
        for the given order.
        """

        payment = await self._get_by_order_id(
            order_id
        )

        return payment is not None

    async def update_payment_status(
        self,
        payment: Payment,
        status: PaymentStatus,
    ) -> Payment:
        """
        Generic payment status updater.
        """

        payment.status = status

        await self.db.commit()

        await self.db.refresh(payment)

        logger.info(
            "Payment %s updated to %s",
            payment.id,
            status.value,
        )

        return payment

    async def delete_payment(
        self,
        payment_id: str,
    ) -> bool:
        """
        Delete payment (admin only).
        """

        payment = await self.get_payment(
            payment_id
        )

        if payment is None:
            return False

        await self.db.delete(payment)

        await self.db.commit()

        logger.warning(
            "Payment %s deleted.",
            payment.id,
        )

        return True