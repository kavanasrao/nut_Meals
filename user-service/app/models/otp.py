"""OTP (one-time password) ORM model.

Used for OTP-based login/verification over SMS or Email. Codes are stored
hashed (never in plaintext) and are single-purpose, single-use, short-lived.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class OtpChannel(str, enum.Enum):
    SMS = "sms"
    EMAIL = "email"


class OtpPurpose(str, enum.Enum):
    LOGIN = "login"
    VERIFY_PHONE = "verify_phone"
    VERIFY_EMAIL = "verify_email"


class OtpCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # email address or E.164 phone number the OTP was issued for
    identifier: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    channel: Mapped[OtpChannel] = mapped_column(
        SAEnum(OtpChannel, name="otp_channel_enum", create_type=True), nullable=False
    )
    purpose: Mapped[OtpPurpose] = mapped_column(
        SAEnum(OtpPurpose, name="otp_purpose_enum", create_type=True),
        nullable=False,
        default=OtpPurpose.LOGIN,
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
