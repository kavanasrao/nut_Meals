from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LoyaltyTransactionType
from app.models.loyalty_transaction import LoyaltyTransaction
from app.repositories.base_repository import BaseRepository


class LoyaltyRepository(BaseRepository[LoyaltyTransaction]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(LoyaltyTransaction, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[LoyaltyTransaction]:
        result = await self.db.execute(
            select(LoyaltyTransaction)
            .where(
                LoyaltyTransaction.customer_id == customer_id,
                LoyaltyTransaction.is_deleted.is_(False),
            )
            .order_by(desc(LoyaltyTransaction.created_at))
        )
        return result.scalars().all()

    async def get_by_transaction_type(
        self,
        customer_id: UUID,
        transaction_type: LoyaltyTransactionType,
    ) -> list[LoyaltyTransaction]:
        result = await self.db.execute(
            select(LoyaltyTransaction)
            .where(
                LoyaltyTransaction.customer_id == customer_id,
                LoyaltyTransaction.transaction_type == transaction_type,
                LoyaltyTransaction.is_deleted.is_(False),
            )
            .order_by(desc(LoyaltyTransaction.created_at))
        )
        return result.scalars().all()

    async def get_current_balance(
        self,
        customer_id: UUID,
    ) -> int:
        result = await self.db.execute(
            select(LoyaltyTransaction)
            .where(
                LoyaltyTransaction.customer_id == customer_id,
                LoyaltyTransaction.is_deleted.is_(False),
            )
            .order_by(desc(LoyaltyTransaction.created_at))
            .limit(1)
        )

        transaction = result.scalar_one_or_none()

        return transaction.balance_after if transaction else 0

    async def get_total_points_earned(
        self,
        customer_id: UUID,
    ) -> int:
        result = await self.db.execute(
            select(LoyaltyTransaction)
            .where(
                LoyaltyTransaction.customer_id == customer_id,
                LoyaltyTransaction.transaction_type == LoyaltyTransactionType.EARN,
                LoyaltyTransaction.is_deleted.is_(False),
            )
        )

        transactions = result.scalars().all()

        return sum(transaction.points for transaction in transactions)
    