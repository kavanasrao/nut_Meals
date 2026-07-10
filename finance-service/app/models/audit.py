"""
Audit log for every mutating action against financial data.

Written to by app.core.audit.write_audit_log(), which is invoked from
service-layer functions (never skipped, even for internal/system actions).
Audit rows are append-only: no UPDATE/DELETE endpoints exist for this table,
and DB-level privileges should enforce INSERT-only for the app's DB role
in production (see ops/db_grants.sql).
"""

import enum
import uuid

from sqlalchemy import Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AuditAction(str, enum.Enum):
    JOURNAL_ENTRY_CREATED = "journal_entry_created"
    JOURNAL_ENTRY_POSTED = "journal_entry_posted"
    JOURNAL_ENTRY_REVERSED = "journal_entry_reversed"
    LEDGER_ACCOUNT_CREATED = "ledger_account_created"
    LEDGER_ACCOUNT_UPDATED = "ledger_account_updated"
    SETTLEMENT_IMPORTED = "settlement_imported"
    RECONCILIATION_RUN_STARTED = "reconciliation_run_started"
    RECONCILIATION_RUN_COMPLETED = "reconciliation_run_completed"
    RECONCILIATION_EXCEPTION_RESOLVED = "reconciliation_exception_resolved"
    REPORT_EXPORTED = "report_exported"


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_actor", "actor"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    actor: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Authenticated principal (user/service) that performed the action"
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
