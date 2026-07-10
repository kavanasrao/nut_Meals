"""
Models for AI-crawler discovery readiness and audit logging.

`AiExportBatch` tracks generated bulk catalog exports (JSONL/NDJSON)
consumed by AI search/embedding pipelines (our own, or third-party
crawlers respecting /ai-sitemap.xml + robots directives).

`AuditLogEntry` records every mutating action against SEO endpoints
(RBAC subject, action, target, before/after) to satisfy the security
requirement for audit trails.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class AiExportBatch(Base):
    """A generated bulk export of catalog data for AI ingestion."""

    __tablename__ = "ai_export_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[ExportStatus] = mapped_column(
        Enum(ExportStatus, name="ai_export_status"), default=ExportStatus.PENDING
    )
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLogEntry(Base):
    """Immutable audit trail row for SEO service admin/mutating actions."""

    __tablename__ = "audit_log_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    actor_subject: Mapped[str] = mapped_column(String(128), nullable=False)  # JWT `sub`
    actor_role: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. "redirect.create"
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
