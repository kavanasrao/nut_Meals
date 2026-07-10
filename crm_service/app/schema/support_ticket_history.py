from uuid import UUID

from app.models.enums import TicketStatus
from app.schemas.base import BaseSchema, TimestampSchema


class SupportTicketHistoryBase(BaseSchema):
    ticket_id: UUID

    previous_status: TicketStatus | None = None

    new_status: TicketStatus

    changed_by: UUID

    comment: str | None = None


class SupportTicketHistoryCreate(SupportTicketHistoryBase):
    pass


class SupportTicketHistoryUpdate(BaseSchema):
    previous_status: TicketStatus | None = None
    new_status: TicketStatus | None = None
    changed_by: UUID | None = None
    comment: str | None = None


class SupportTicketHistoryResponse(
    SupportTicketHistoryBase,
    TimestampSchema,
):
    pass


class SupportTicketHistoryListResponse(BaseSchema):
    total: int
    items: list[SupportTicketHistoryResponse]
    