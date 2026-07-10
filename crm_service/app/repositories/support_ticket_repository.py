from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TicketPriority, TicketStatus
from app.models.support_ticket import SupportTicket
from app.repositories.base_repository import BaseRepository


class SupportTicketRepository(BaseRepository[SupportTicket]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(SupportTicket, db)

    async def get_by_ticket_number(
        self,
        ticket_number: str,
    ) -> SupportTicket | None:
        result = await self.db.execute(
            select(SupportTicket).where(
                SupportTicket.ticket_number == ticket_number,
                SupportTicket.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket)
            .where(
                SupportTicket.customer_id == customer_id,
                SupportTicket.is_deleted.is_(False),
            )
            .order_by(desc(SupportTicket.created_at))
        )
        return result.scalars().all()

    async def get_by_status(
        self,
        status: TicketStatus,
    ) -> list[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket)
            .where(
                SupportTicket.status == status,
                SupportTicket.is_deleted.is_(False),
            )
            .order_by(desc(SupportTicket.created_at))
        )
        return result.scalars().all()

    async def get_by_priority(
        self,
        priority: TicketPriority,
    ) -> list[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket)
            .where(
                SupportTicket.priority == priority,
                SupportTicket.is_deleted.is_(False),
            )
            .order_by(desc(SupportTicket.created_at))
        )
        return result.scalars().all()

    async def get_assigned_tickets(
        self,
        agent_id: UUID,
    ) -> list[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket)
            .where(
                SupportTicket.assigned_to == agent_id,
                SupportTicket.is_deleted.is_(False),
            )
            .order_by(desc(SupportTicket.created_at))
        )
        return result.scalars().all()

    async def update_status(
        self,
        ticket_id: UUID,
        status: TicketStatus,
    ) -> SupportTicket | None:
        ticket = await self.get_by_id(ticket_id)

        if ticket is None:
            return None

        ticket.status = status

        await self.db.commit()
        await self.db.refresh(ticket)

        return ticket