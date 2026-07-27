"""
Affiliate Click schemas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DeviceType(str, Enum):
    DESKTOP = "DESKTOP"
    MOBILE = "MOBILE"
    TABLET = "TABLET"
    OTHER = "OTHER"


# ==========================================================
# Base
# ==========================================================

class AffiliateClickBase(BaseModel):
    affiliate_id: UUID

    referral_code: str = Field(..., max_length=40)

    ip_address: str | None = Field(default=None, max_length=45)

    user_agent: str | None = Field(
        default=None,
        max_length=500,
    )

    device_type: DeviceType = DeviceType.OTHER

    browser: str | None = Field(
        default=None,
        max_length=100,
    )

    operating_system: str | None = Field(
        default=None,
        max_length=100,
    )

    country: str | None = Field(
        default=None,
        max_length=100,
    )

    state: str | None = Field(
        default=None,
        max_length=100,
    )

    city: str | None = Field(
        default=None,
        max_length=100,
    )

    landing_page: str | None = Field(
        default=None,
        max_length=500,
    )

    referrer_url: str | None = Field(
        default=None,
        max_length=500,
    )

    session_id: str | None = Field(
        default=None,
        max_length=120,
    )


# ==========================================================
# Create
# ==========================================================

class AffiliateClickCreate(AffiliateClickBase):
    pass


# ==========================================================
# Update
# ==========================================================

class AffiliateClickUpdate(BaseModel):
    converted: bool | None = None

    converted_order_id: UUID | None = None


# ==========================================================
# Response
# ==========================================================

class AffiliateClickResponse(AffiliateClickBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    converted: bool

    converted_order_id: UUID | None

    clicked_at: datetime