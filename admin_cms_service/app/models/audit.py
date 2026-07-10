"""
ORM model for the admin audit log. Every state-changing admin action
(approve/reject return, publish content, export a report, etc.) writes
an entry here -- see app/core/audit.py for the write helper.
"""
import uuid
from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class AuditLogEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "audit_log_entries"

    actor_admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "return.approve"
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "return_request"
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    request_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
