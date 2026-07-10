from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
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
from app.services.analytics_service import AnalyticsService

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsService:
    return AnalyticsService(
        customer_repository=CustomerProfileRepository(db),
        loyalty_repository=LoyaltyRepository(db),
        feedback_repository=FeedbackRepository(db),
        ticket_repository=SupportTicketRepository(db),
    )


@router.get("/customer/{customer_id}")
async def customer_overview(
    customer_id: UUID,
    service: AnalyticsService = Depends(get_service),
):
    return await service.customer_overview(customer_id)


@router.get("/customer/{customer_id}/loyalty")
async def loyalty_summary(
    customer_id: UUID,
    service: AnalyticsService = Depends(get_service),
):
    return await service.loyalty_summary(customer_id)


@router.get("/customer/{customer_id}/support")
async def support_summary(
    customer_id: UUID,
    service: AnalyticsService = Depends(get_service),
):
    return await service.support_summary(customer_id)


@router.get("/customer/{customer_id}/feedback")
async def feedback_summary(
    customer_id: UUID,
    service: AnalyticsService = Depends(get_service),
):
    return await service.feedback_summary(customer_id)