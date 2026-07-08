"""ORM models for the Admin Service.

Three tables owned exclusively by this service:
  - admin_users    — admin panel accounts with roles
  - system_config  — key/value runtime configuration
  - audit_logs     — immutable trail of every admin action
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


# ── Enumerations ─────────────────────────────────────────────────────────────

class AdminRole(str, enum.Enum):
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


# ── AdminUser ────────────────────────────────────────────────────────────────

class AdminUser(Base):
    """Admin panel accounts. Completely separate from end-user accounts."""

    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        SAEnum(AdminRole, name="admin_role_enum", create_type=True),
        nullable=False,
        default=AdminRole.ADMIN,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── SystemConfig ─────────────────────────────────────────────────────────────

class SystemConfig(Base):
    """
    Key/value store for runtime configuration.

    Examples:
      payment_provider → "juspay"
      whatsapp_provider → "twilio"
      home_delivery_enabled → "true"

    The value column is TEXT so any serialised type can be stored.
    Services poll this table (or receive events) to pick up changes.
    """

    __tablename__ = "system_config"
    __table_args__ = (UniqueConstraint("key", name="uq_system_config_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    updated_by: Mapped[str | None] = mapped_column(String(255))  # admin email
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ── AuditLog ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable record of every admin action for security and compliance.

    Never update or delete rows in this table.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    admin_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    admin_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    admin_role: Mapped[str] = mapped_column(String(50), nullable=False)

    # What happened
    action: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "order"
    resource_id: Mapped[str | None] = mapped_column(String(255), index=True)

    # HTTP context
    http_method: Mapped[str | None] = mapped_column(String(10))
    http_path: Mapped[str | None] = mapped_column(String(1024))
    ip_address: Mapped[str | None] = mapped_column(String(45))

    # Payload snapshot (sanitised — no passwords)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    response_status: Mapped[int | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
