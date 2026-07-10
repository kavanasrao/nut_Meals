"""
Settlement Service.

Handles:
- Settlement import
- Payment reconciliation
- Settlement lookup
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.events import EventType
from app.events.publisher import EventPublisher
from app.models.payment import Payment
from app.models.settlement import (
    Settlement,
    SettlementStatus,
)
from app.providers.factory import get_payment_provider

logger = logging.getLogger(__name__)


class SettlementService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = get_payment_provider()

    # -----------------------------------------------------
    # Import settlement report from payment gateway
    # -----------------------------------------------------

    async def import_settlements(self) -> list[Settlement]:

        reports = await self.provider.fetch_settlements()

        settlements: list[Settlement] = []

        for report in reports:

            existing = await self.db.execute(
                select(Settlement).where(
                    Settlement.settlement_reference
                    == report.settlement_reference
                )
            )

            if existing.scalar_one_or_none():
                continue

            settlement = Settlement(
                gateway=report.provider,
                settlement_reference=report.settlement_reference,
                amount=report.amount,
                currency=report.currency,
                settlement_date=report.settlement_date,
                status=SettlementStatus.PENDING,
                gateway_report=report.raw,
            )

            self.db.add(settlement)

            settlements.append(settlement)

        await self.db.commit()

        for settlement in settlements:

            await EventPublisher.publish(
                EventType.SETTLEMENT_IMPORTED,
                {
                    "settlement_id": str(settlement.id),
                    "reference": settlement.settlement_reference,
                    "amount": str(settlement.amount),
                },
            )

        logger.info(
            "%d settlements imported.",
            len(settlements),
        )

        return settlements

    # -----------------------------------------------------
    # Reconcile settlement with payments
    # -----------------------------------------------------

    async def reconcile(
        self,
        settlement_id: UUID | str,
    ) -> Settlement:

        settlement = await self.db.get(
            Settlement,
            settlement_id,
        )

        if settlement is None:
            raise ValueError("Settlement not found.")

        payment = await self.db.execute(
            select(Payment).where(
                Payment.provider_payment_id
                == settlement.settlement_reference
            )
        )

        payment = payment.scalar_one_or_none()

        if payment is None:

            settlement.status = SettlementStatus.MISMATCH

            await EventPublisher.publish(
                EventType.SETTLEMENT_MISMATCH,
                {
                    "settlement_id": str(settlement.id),
                    "reference": settlement.settlement_reference,
                },
            )

        else:

            if Decimal(payment.amount) == Decimal(settlement.amount):

                settlement.status = SettlementStatus.RECONCILED

                await EventPublisher.publish(
                    EventType.SETTLEMENT_RECONCILED,
                    {
                        "settlement_id": str(settlement.id),
                        "payment_id": str(payment.id),
                    },
                )

            else:

                settlement.status = SettlementStatus.MISMATCH

                await EventPublisher.publish(
                    EventType.SETTLEMENT_MISMATCH,
                    {
                        "settlement_id": str(settlement.id),
                        "payment_id": str(payment.id),
                    },
                )

        await self.db.commit()

        await self.db.refresh(settlement)

        return settlement

    # -----------------------------------------------------
    # Queries
    # -----------------------------------------------------

    async def get_settlement(
        self,
        settlement_id: UUID | str,
    ) -> Settlement | None:

        return await self.db.get(
            Settlement,
            settlement_id,
        )

    async def list_settlements(
        self,
    ) -> list[Settlement]:

        result = await self.db.execute(
            select(Settlement).order_by(
                Settlement.created_at.desc()
            )
        )

        return list(result.scalars().all())