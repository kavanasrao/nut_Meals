from uuid import UUID

from app.models.enums import LoyaltyTransactionType
from app.models.loyalty_transaction import LoyaltyTransaction
from app.repositories.loyalty_repository import (
    LoyaltyRepository,
)
from app.schemas.loyalty_transaction import (
    LoyaltyTransactionCreate,
    LoyaltyTransactionUpdate,
)


class LoyaltyService:
    def __init__(
        self,
        repository: LoyaltyRepository,
    ) -> None:
        self.repository = repository

    async def create_transaction(
        self,
        data: LoyaltyTransactionCreate,
    ) -> LoyaltyTransaction:
        transaction = LoyaltyTransaction(**data.model_dump())
        return await self.repository.create(transaction)

    async def get_transaction(
        self,
        transaction_id: UUID,
    ) -> LoyaltyTransaction | None:
        return await self.repository.get_by_id(transaction_id)

    async def get_customer_transactions(
        self,
        customer_id: UUID,
    ) -> list[LoyaltyTransaction]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_transactions_by_type(
        self,
        customer_id: UUID,
        transaction_type: LoyaltyTransactionType,
    ) -> list[LoyaltyTransaction]:
        return await self.repository.get_by_transaction_type(
            customer_id,
            transaction_type,
        )

    async def get_current_balance(
        self,
        customer_id: UUID,
    ) -> int:
        return await self.repository.get_current_balance(customer_id)

    async def get_total_points_earned(
        self,
        customer_id: UUID,
    ) -> int:
        return await self.repository.get_total_points_earned(customer_id)

    async def update_transaction(
        self,
        transaction_id: UUID,
        data: LoyaltyTransactionUpdate,
    ) -> LoyaltyTransaction | None:
        transaction = await self.repository.get_by_id(transaction_id)

        if transaction is None:
            return None

        return await self.repository.update(
            transaction,
            data.model_dump(exclude_unset=True),
        )

    async def delete_transaction(
        self,
        transaction_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(transaction_id)