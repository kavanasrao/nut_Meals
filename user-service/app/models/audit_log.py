"""User audit log ORM model.

Append-only trail of security-sensitive and profile-changing actions,
scoped to the User Service (mirrors the account-level events that
security-service's central audit log tracks at the platform level).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    OTP_LOGIN = "otp_login"
    SOCIAL_LOGIN = "social_login"
    LOGOUT = "logout"
    PROFILE_UPDATE = "profile_update"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    ADDRESS_CREATE = "address_create"
    ADDRESS_UPDATE = "address_update"
    ADDRESS_DELETE = "address_delete"
    ADDRESS_SET_DEFAULT = "address_set_default"
    PREFERENCE_UPDATE = "preference_update"
    ACCOUNT_BLOCKED = "account_blocked"
    ACCOUNT_UNBLOCKED = "account_unblocked"
    ROLE_CHANGED = "role_changed"


class UserAuditLog(Base):
    __tablename__ = "user_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable: some events (e.g. failed login with an unknown email) have no user yet.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="user_audit_action_enum", create_type=True),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
