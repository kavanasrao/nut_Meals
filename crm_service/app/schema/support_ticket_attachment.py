from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class SupportTicketAttachmentBase(BaseSchema):
    ticket_id: UUID

    file_name: str = Field(..., max_length=255)

    file_url: str = Field(..., max_length=500)

    file_type: str = Field(..., max_length=100)

    file_size: int

    uploaded_by: UUID


class SupportTicketAttachmentCreate(SupportTicketAttachmentBase):
    pass


class SupportTicketAttachmentUpdate(BaseSchema):
    file_name: str | None = Field(default=None, max_length=255)
    file_url: str | None = Field(default=None, max_length=500)
    file_type: str | None = Field(default=None, max_length=100)
    file_size: int | None = None


class SupportTicketAttachmentResponse(
    SupportTicketAttachmentBase,
    TimestampSchema,
):
    pass


class SupportTicketAttachmentListResponse(BaseSchema):
    total: int
    items: list[SupportTicketAttachmentResponse]
    