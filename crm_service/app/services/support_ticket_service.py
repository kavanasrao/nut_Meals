from uuid import UUID

from app.models.enums import TicketPriority, TicketStatus
from app.models.support_ticket import SupportTicket
from app.repositories.support_ticket_repository import (
    SupportTicketRepository,
)
from app.schemas.support_ticket import (
    SupportTicketCreate,
    SupportTicketUpdate,
)


class SupportTicketService:
    def __init__(
        self,
        repository: SupportTicketRepository,
    ) -> None:
        self.repository = repository

    async def create_ticket(
        self,
        data: SupportTicketCreate,
    ) -> SupportTicket:
        ticket = SupportTicket(**data.model_dump())
        return await self.repository.create(ticket)

    async def get_ticket(
        self,
        ticket_id: UUID,
    ) -> SupportTicket | None:
        return await self.repository.get_by_id(ticket_id)

    async def get_ticket_by_number(
        self,
        ticket_number: str,
    ) -> SupportTicket | None:
        return await self.repository.get_by_ticket_number(ticket_number)

    async def get_customer_tickets(
        self,
        customer_id: UUID,
    ) -> list[SupportTicket]:
        return await self.repository.get_by_customer_id(customer_id)

    async def get_tickets_by_status(
        self,
        status: TicketStatus,
    ) -> list[SupportTicket]:
        return await self.repository.get_by_status(status)

    async def get_tickets_by_priority(
        self,
        priority: TicketPriority,
    ) -> list[SupportTicket]:
        return await self.repository.get_by_priority(priority)

    async def get_agent_tickets(
        self,
        agent_id: UUID,
    ) -> list[SupportTicket]:
        return await self.repository.get_assigned_tickets(agent_id)

    async def update_ticket(
        self,
        ticket_id: UUID,
        data: SupportTicketUpdate,
    ) -> SupportTicket | None:
        ticket = await self.repository.get_by_id(ticket_id)

        if ticket is None:
            return None

        return await self.repository.update(
            ticket,
            data.model_dump(exclude_unset=True),
        )

    async def update_status(
        self,
        ticket_id: UUID,
        status: TicketStatus,
    ) -> SupportTicket | None:
        return await self.repository.update_status(
            ticket_id,
            status,
        )

    async def delete_ticket(
        self,
        ticket_id: UUID,
    ) -> bool:
        return await self.repository.soft_delete(ticket_id)