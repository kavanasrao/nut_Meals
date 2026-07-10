from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema


class SupportTicketNoteBase(BaseSchema):
    ticket_id: UUID

    author_id: UUID

    note: str

    is_internal: bool = True


class SupportTicketNoteCreate(SupportTicketNoteBase):
    pass


class SupportTicketNoteUpdate(BaseSchema):
    note: str | None = None
    is_internal: bool | None = None


class SupportTicketNoteResponse(
    SupportTicketNoteBase,
    TimestampSchema,
):
    pass


class SupportTicketNoteListResponse(BaseSchema):
    total: int
    items: list[SupportTicketNoteResponse]
    