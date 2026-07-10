from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.campaign_repository import CampaignRepository
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
from app.services.report_service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> ReportService:
    return ReportService(
        customer_repository=CustomerProfileRepository(db),
        loyalty_repository=LoyaltyRepository(db),
        campaign_repository=CampaignRepository(db),
        feedback_repository=FeedbackRepository(db),
        ticket_repository=SupportTicketRepository(db),
    )


@router.get("/customers")
async def customer_report(
    service: ReportService = Depends(get_service),
):
    return await service.customer_report()


@router.get("/loyalty")
async def loyalty_report(
    service: ReportService = Depends(get_service),
):
    return await service.loyalty_report()


@router.get("/campaigns")
async def campaign_report(
    service: ReportService = Depends(get_service),
):
    return await service.campaign_report()


@router.get("/feedback")
async def feedback_report(
    service: ReportService = Depends(get_service),
):
    return await service.feedback_report()


@router.get("/support")
async def support_report(
    service: ReportService = Depends(get_service),
):
    return await service.support_report()


@router.get("/dashboard")
async def dashboard_summary(
    service: ReportService = Depends(get_service),
):
    return await service.dashboard_summary()