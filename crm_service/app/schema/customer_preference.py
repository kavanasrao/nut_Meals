from uuid import UUID

from app.schemas.base import BaseSchema, TimestampSchema


class CustomerPreferenceBase(BaseSchema):
    customer_id: UUID

    language: str = "en"
    currency: str = "INR"

    email_notifications: bool = True
    sms_notifications: bool = True
    whatsapp_notifications: bool = True
    push_notifications: bool = True

    marketing_emails: bool = True
    marketing_sms: bool = False
    marketing_whatsapp: bool = False


class CustomerPreferenceCreate(CustomerPreferenceBase):
    pass


class CustomerPreferenceUpdate(BaseSchema):
    language: str | None = None
    currency: str | None = None

    email_notifications: bool | None = None
    sms_notifications: bool | None = None
    whatsapp_notifications: bool | None = None
    push_notifications: bool | None = None

    marketing_emails: bool | None = None
    marketing_sms: bool | None = None
    marketing_whatsapp: bool | None = None


class CustomerPreferenceResponse(
    CustomerPreferenceBase,
    TimestampSchema,
):
    pass


class CustomerPreferenceListResponse(BaseSchema):
    total: int
    items: list[CustomerPreferenceResponse]
    