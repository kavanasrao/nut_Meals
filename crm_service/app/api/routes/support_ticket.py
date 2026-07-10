from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.repositories.support_ticket_repository import (
    SupportTicketRepository,
)
from app.schema.support_ticket import (
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTicketUpdate,
)
from app.services.support_ticket_service import (
    SupportTicketService,
)

router = APIRouter(
    prefix="/support-tickets",
    tags=["Support Tickets"],
)


def get_service(
    db: AsyncSession = Depends(get_db),
) -> SupportTicketService:
    repository = SupportTicketRepository(db)
    return SupportTicketService(repository)


@router.post(
    "/",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    payload: SupportTicketCreate,
    service: SupportTicketService = Depends(get_service),
):
    return await service.create_ticket(payload)


@router.get(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
)
async def get_ticket(
    ticket_id: UUID,
    service: SupportTicketService = Depends(get_service),
):
    ticket = await service.get_ticket(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Support ticket not found",
        )

    return ticket


@router.get("/customer/{customer_id}")
async def get_customer_tickets(
    customer_id: UUID,
    service: SupportTicketService = Depends(get_service),
):
    return await service.get_customer_tickets(customer_id)


@router.put(
    "/{ticket_id}",
    response_model=SupportTicketResponse,
)
async def update_ticket(
    ticket_id: UUID,
    payload: SupportTicketUpdate,
    service: SupportTicketService = Depends(get_service),
):
    ticket = await service.update_ticket(
        ticket_id,
        payload,
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="Support ticket not found",
        )

    return ticket


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: UUID,
    service: SupportTicketService = Depends(get_service),
):
    deleted = await service.delete_ticket(ticket_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Support ticket not found",
        )

    return {
        "message": "Support ticket deleted successfully"
    }