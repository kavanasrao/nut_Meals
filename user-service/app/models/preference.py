"""Customer preferences ORM model — one row per user (1:1)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    dark_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sms_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
