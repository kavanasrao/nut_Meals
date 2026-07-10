"""
Audit log models.

Every critical action across nut_meals services (order placed/cancelled,
payment captured/refunded, inventory adjusted, role granted, WAF rule
changed, compliance report exported, etc.) is expected to emit an audit
event. Services publish events to Redis/Celery (see app/tasks/audit_tasks.py);
this table is the durable, queryable store behind that pipeline.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditLog(Base):
    """A single structured, immutable audit record.

    Records are write-once: the API layer only ever INSERTs; there are no
    update/delete routes exposed for audit logs (compliance requirement).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_service_created", "service", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    action: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True, doc="e.g. 'order.created', 'payment.refunded'"
    )
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    severity: Mapped[AuditSeverity] = mapped_column(Enum(AuditSeverity), default=AuditSeverity.INFO)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, doc="Arbitrary structured context, e.g. before/after diff"
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class AuditExportJob(Base):
    """Tracks async export jobs (CSV/JSON dumps of audit logs for auditors)."""

    __tablename__ = "audit_export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requested_by: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|completed|failed
    filters_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
