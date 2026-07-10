from app.repositories.campaign_repository import CampaignRepository
from app.repositories.customer_profile_repository import (
    CustomerProfileRepository,
)
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.loyalty_repository import LoyaltyRepository
from app.repositories.support_ticket_repository import (
    SupportTicketRepository,
)


class ReportService:
    def __init__(
        self,
        customer_repository: CustomerProfileRepository,
        loyalty_repository: LoyaltyRepository,
        campaign_repository: CampaignRepository,
        feedback_repository: FeedbackRepository,
        ticket_repository: SupportTicketRepository,
    ) -> None:
        self.customer_repository = customer_repository
        self.loyalty_repository = loyalty_repository
        self.campaign_repository = campaign_repository
        self.feedback_repository = feedback_repository
        self.ticket_repository = ticket_repository

    async def customer_report(self) -> dict:
        customers = await self.customer_repository.get_all()

        return {
            "total_customers": len(customers),
            "active_customers": len(
                [c for c in customers if c.is_active]
            ),
            "inactive_customers": len(
                [c for c in customers if not c.is_active]
            ),
        }

    async def loyalty_report(self) -> dict:
        transactions = await self.loyalty_repository.get_all()

        earned = sum(
            t.points
            for t in transactions
            if t.transaction_type.value == "EARN"
        )

        redeemed = sum(
            t.points
            for t in transactions
            if t.transaction_type.value == "REDEEM"
        )

        return {
            "total_transactions": len(transactions),
            "points_earned": earned,
            "points_redeemed": redeemed,
        }

    async def campaign_report(self) -> dict:
        campaigns = await self.campaign_repository.get_all()

        return {
            "total_campaigns": len(campaigns),
            "draft_campaigns": len(
                [c for c in campaigns if c.status.value == "DRAFT"]
            ),
            "scheduled_campaigns": len(
                [c for c in campaigns if c.status.value == "SCHEDULED"]
            ),
            "completed_campaigns": len(
                [c for c in campaigns if c.status.value == "COMPLETED"]
            ),
        }

    async def feedback_report(self) -> dict:
        feedback = await self.feedback_repository.get_all()

        return {
            "total_feedback": len(feedback),
            "resolved_feedback": len(
                [f for f in feedback if f.is_resolved]
            ),
            "pending_feedback": len(
                [f for f in feedback if not f.is_resolved]
            ),
        }

    async def support_report(self) -> dict:
        tickets = await self.ticket_repository.get_all()

        return {
            "total_tickets": len(tickets),
            "open_tickets": len(
                [t for t in tickets if t.status.value == "OPEN"]
            ),
            "resolved_tickets": len(
                [t for t in tickets if t.status.value == "RESOLVED"]
            ),
            "closed_tickets": len(
                [t for t in tickets if t.status.value == "CLOSED"]
            ),
        }

    async def dashboard_summary(self) -> dict:
        return {
            "customers": await self.customer_report(),
            "loyalty": await self.loyalty_report(),
            "campaigns": await self.campaign_report(),
            "feedback": await self.feedback_report(),
            "support": await self.support_report(),
        }