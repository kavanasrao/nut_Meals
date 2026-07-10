from datetime import datetime
from uuid import UUID
from decimal import Decimal

from app.models.enums import LoyaltyTransactionType
from app.schemas.base import BaseSchema, TimestampSchema


class LoyaltyTransactionBase(BaseSchema):
    customer_id: UUID

    transaction_type: LoyaltyTransactionType

    points: int

    balance_after: int

    monetary_value: Decimal | None = None

    reference_type: str | None = None

    reference_id: UUID | None = None

    description: str | None = None

    expires_at: datetime | None = None


class LoyaltyTransactionCreate(LoyaltyTransactionBase):
    pass


class LoyaltyTransactionUpdate(BaseSchema):
    points: int | None = None
    balance_after: int | None = None
    monetary_value: Decimal | None = None
    description: str | None = None
    expires_at: datetime | None = None


class LoyaltyTransactionResponse(
    LoyaltyTransactionBase,
    TimestampSchema,
):
    pass


class LoyaltyTransactionListResponse(BaseSchema):
    total: int
    items: list[LoyaltyTransactionResponse]
    