from uuid import UUID

from app.models.customer_feedback import CustomerFeedback
from app.models.enums import FeedbackRating
from app.repositories.feedback_repository import (
    FeedbackRepository,
)
from app.schemas.customer_feedback import (
    CustomerFeedbackCreate,
    CustomerFeedbackUpdate,
)


class FeedbackService:
    def __init__(
        self,
        repository: FeedbackRepository,
    ) -> None:
        self.repository = repository

    async def create_feedback(
        self,
        data: CustomerFeedbackCreate,
    ) -> CustomerFeedback:
        feedback = CustomerFeedback(**data.model_dump())
        return await self.repository.create(feedback)

    async def get_feedback(
        self,
        feedback_id: UUID,
    ) -> CustomerFeedback | None:
        return await self.repository.get_by_id(feedback_id)

    async def get_customer_feedback(
        self,
        customer_id: UUID,
    ) -> list[CustomerFeedback]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_feedback_by_ticket(
        self,
        ticket_id: UUID,
    ) -> list[CustomerFeedback]:
        return await self.repository.get_by_ticket_id(ticket_id)

    async def get_feedback_by_rating(
        self,
        rating: FeedbackRating,
    ) -> list[CustomerFeedback]:
        return await self.repository.get_by_rating(rating)

    async def get_unresolved_feedback(
        self,
    ) -> list[CustomerFeedback]:
        return await self.repository.get_unresolved()

    async def mark_resolved(
        self,
        feedback_id: UUID,
    ) -> CustomerFeedback | None:
        return await self.repository.mark_resolved(feedback_id)

    async def update_feedback(
        self,
        feedback_id: UUID,
        data: CustomerFeedbackUpdate,
    ) -> CustomerFeedback | None:
        feedback = await self.repository.get_by_id(feedback_id)

        if feedback is None:
            return None

        return await self.repository.update(
            feedback,
            data.model_dump(exclude_unset=True),
        )

    async def delete_feedback(
        self,
        feedback_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(feedback_id)