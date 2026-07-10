from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.enums import (
    AcquisitionChannel,
    CustomerSource,
    CustomerStatus,
    LoyaltyTier,
)
from app.schemas.base import BaseSchema, TimestampSchema


class CustomerProfileBase(BaseSchema):
    user_id: UUID
    customer_code: str = Field(..., max_length=30)

    status: CustomerStatus = CustomerStatus.ACTIVE
    source: CustomerSource = CustomerSource.WEBSITE
    acquisition_channel: AcquisitionChannel = AcquisitionChannel.ORGANIC

    loyalty_tier: LoyaltyTier = LoyaltyTier.BRONZE
    loyalty_points: int = 0
    lifetime_value: Decimal = Decimal("0.00")


class CustomerProfileCreate(CustomerProfileBase):
    pass


class CustomerProfileUpdate(BaseSchema):
    status: CustomerStatus | None = None
    source: CustomerSource | None = None
    acquisition_channel: AcquisitionChannel | None = None

    loyalty_tier: LoyaltyTier | None = None
    loyalty_points: int | None = None
    lifetime_value: Decimal | None = None


class CustomerProfileResponse(
    CustomerProfileBase,
    TimestampSchema,
):
    pass


class CustomerProfileListResponse(BaseSchema):
    total: int
    items: list[CustomerProfileResponse]