from uuid import UUID

from app.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.repositories.feedback_repository import (
    FeedbackRepository,
)
from app.repositories.loyalty_repository import (
    LoyaltyRepository,
)
from app.repositories.support_ticket_repository import (
    SupportTicketRepository,
)


class AnalyticsService:
    def __init__(
        self,
        customer_repository: CustomerProfileRepository,
        loyalty_repository: LoyaltyRepository,
        feedback_repository: FeedbackRepository,
        ticket_repository: SupportTicketRepository,
    ) -> None:
        self.customer_repository = customer_repository
        self.loyalty_repository = loyalty_repository
        self.feedback_repository = feedback_repository
        self.ticket_repository = ticket_repository

    async def customer_overview(
        self,
        customer_id: UUID,
    ) -> dict:
        customer = await self.customer_repository.get_by_id(customer_id)

        loyalty = await self.loyalty_repository.get_current_balance(
            customer_id
        )

        feedback = await self.feedback_repository.get_by_customer_id(
            customer_id
        )

        tickets = await self.ticket_repository.get_by_customer_id(
            customer_id
        )

        average_rating = (
            round(
                sum(item.rating.value for item in feedback)
                / len(feedback),
                2,
            )
            if feedback
            else 0
        )

        return {
            "customer": customer,
            "loyalty_points": loyalty,
            "feedback_count": len(feedback),
            "average_rating": average_rating,
            "support_ticket_count": len(tickets),
        }

    async def loyalty_summary(
        self,
        customer_id: UUID,
    ) -> dict:
        return {
            "current_balance": await self.loyalty_repository.get_current_balance(
                customer_id
            ),
            "earned_points": await self.loyalty_repository.get_total_points_earned(
                customer_id
            ),
        }

    async def support_summary(
        self,
        customer_id: UUID,
    ) -> dict:
        tickets = await self.ticket_repository.get_by_customer_id(
            customer_id
        )

        return {
            "total_tickets": len(tickets),
            "open_tickets": len(
                [
                    ticket
                    for ticket in tickets
                    if ticket.status.value
                    in {
                        "OPEN",
                        "ASSIGNED",
                        "IN_PROGRESS",
                    }
                ]
            ),
            "closed_tickets": len(
                [
                    ticket
                    for ticket in tickets
                    if ticket.status.value == "CLOSED"
                ]
            ),
        }

    async def feedback_summary(
        self,
        customer_id: UUID,
    ) -> dict:
        feedback = await self.feedback_repository.get_by_customer_id(
            customer_id
        )

        return {
            "total_feedback": len(feedback),
            "resolved_feedback": len(
                [item for item in feedback if item.is_resolved]
            ),
            "pending_feedback": len(
                [item for item in feedback if not item.is_resolved]
            ),
        }
    