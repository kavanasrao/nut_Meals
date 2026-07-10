from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_interaction import CustomerInteraction
from app.models.enums import InteractionType
from app.repositories.base_repository import BaseRepository


class CustomerInteractionRepository(BaseRepository[CustomerInteraction]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerInteraction, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerInteraction]:
        result = await self.db.execute(
            select(CustomerInteraction)
            .where(
                CustomerInteraction.customer_id == customer_id,
                CustomerInteraction.is_deleted.is_(False),
            )
            .order_by(desc(CustomerInteraction.created_at))
        )
        return result.scalars().all()

    async def get_by_type(
        self,
        customer_id: UUID,
        interaction_type: InteractionType,
    ) -> list[CustomerInteraction]:
        result = await self.db.execute(
            select(CustomerInteraction)
            .where(
                CustomerInteraction.customer_id == customer_id,
                CustomerInteraction.interaction_type == interaction_type,
                CustomerInteraction.is_deleted.is_(False),
            )
            .order_by(desc(CustomerInteraction.created_at))
        )
        return result.scalars().all()

    async def get_by_staff(
        self,
        staff_id: UUID,
    ) -> list[CustomerInteraction]:
        result = await self.db.execute(
            select(CustomerInteraction)
            .where(
                CustomerInteraction.performed_by == staff_id,
                CustomerInteraction.is_deleted.is_(False),
            )
            .order_by(desc(CustomerInteraction.created_at))
        )
        return result.scalars().all()