from uuid import UUID

from pydantic import Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.base import BaseSchema, TimestampSchema


class SupportTicketBase(BaseSchema):
    customer_id: UUID

    ticket_number: str = Field(..., max_length=30)

    subject: str = Field(..., max_length=255)

    description: str

    status: TicketStatus = TicketStatus.OPEN

    priority: TicketPriority = TicketPriority.MEDIUM

    assigned_to: UUID | None = None

    resolution: str | None = None


class SupportTicketCreate(SupportTicketBase):
    pass


class SupportTicketUpdate(BaseSchema):
    subject: str | None = Field(
        default=None,
        max_length=255,
    )

    description: str | None = None

    status: TicketStatus | None = None

    priority: TicketPriority | None = None

    assigned_to: UUID | None = None

    resolution: str | None = None


class SupportTicketResponse(
    SupportTicketBase,
    TimestampSchema,
):
    pass


class SupportTicketListResponse(BaseSchema):
    total: int
    items: list[SupportTicketResponse]