from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_feedback import CustomerFeedback
from app.models.enums import FeedbackRating
from app.repositories.base_repository import BaseRepository


class FeedbackRepository(BaseRepository[CustomerFeedback]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerFeedback, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerFeedback]:
        result = await self.db.execute(
            select(CustomerFeedback)
            .where(
                CustomerFeedback.customer_id == customer_id,
                CustomerFeedback.is_deleted.is_(False),
            )
            .order_by(desc(CustomerFeedback.created_at))
        )
        return result.scalars().all()

    async def get_by_ticket_id(
        self,
        ticket_id: UUID,
    ) -> list[CustomerFeedback]:
        result = await self.db.execute(
            select(CustomerFeedback)
            .where(
                CustomerFeedback.ticket_id == ticket_id,
                CustomerFeedback.is_deleted.is_(False),
            )
        )
        return result.scalars().all()

    async def get_by_rating(
        self,
        rating: FeedbackRating,
    ) -> list[CustomerFeedback]:
        result = await self.db.execute(
            select(CustomerFeedback)
            .where(
                CustomerFeedback.rating == rating,
                CustomerFeedback.is_deleted.is_(False),
            )
            .order_by(desc(CustomerFeedback.created_at))
        )
        return result.scalars().all()

    async def get_unresolved(
        self,
    ) -> list[CustomerFeedback]:
        result = await self.db.execute(
            select(CustomerFeedback)
            .where(
                CustomerFeedback.is_resolved.is_(False),
                CustomerFeedback.is_deleted.is_(False),
            )
            .order_by(desc(CustomerFeedback.created_at))
        )
        return result.scalars().all()

    async def mark_resolved(
        self,
        feedback_id: UUID,
    ) -> CustomerFeedback | None:
        feedback = await self.get_by_id(feedback_id)

        if feedback is None:
            return None

        feedback.is_resolved = True

        await self.db.commit()
        await self.db.refresh(feedback)

        return feedback