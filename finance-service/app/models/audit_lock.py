"""
Digital audit lock - period locking for closed accounting months.

Indian GST/tax compliance (and general accounting hygiene) requires that
once a month's books are closed and filed, no further postings can be
backdated into that period. `PeriodLock` is the enforcement record:

  - One row per calendar period ("YYYY-MM").
  - status=OPEN (default): postings dated in this period are allowed.
  - status=LOCKED: JournalService (and, transitively, every service that
    posts through it - GST, credit notes, refunds, reconciliation) rejects
    any create/post/reverse whose `entry_date` falls inside this period.

Locking is normally driven by a scheduled Celery task shortly after month
end (see app.tasks.audit_lock_tasks.auto_lock_previous_month), but can also
be triggered manually by a Finance admin. Unlocking is a deliberate,
audited, admin-only action (e.g. to fix a compliance-mandated correction)
and is itself written to the audit trail via app.core.audit.write_audit_log
with AuditAction.PERIOD_UNLOCKED - it is never silent.

Every lock/unlock transition is required to also produce an AuditLog row
via write_audit_log; this model does not duplicate that history (no
separate "lock audit trail" table) because AuditLog, filtered by
entity_type="period_lock", already *is* the immutable trail of every
locking decision, who made it, and why - which is what the append-only
audit_logs table is for.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.models.mixins import TimestampMixin


class PeriodLockStatus(str, enum.Enum):
    OPEN = "open"
    LOCKED = "locked"


class PeriodLock(TimestampMixin, Base):
    __tablename__ = "period_locks"
    __table_args__ = (
        UniqueConstraint("period", name="uq_period_locks_period"),
        Index("ix_period_locks_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    period: Mapped[str] = mapped_column(String(7), nullable=False, doc="Accounting period, format YYYY-MM")
    status: Mapped[PeriodLockStatus] = mapped_column(
        Enum(PeriodLockStatus, name="period_lock_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=PeriodLockStatus.OPEN,
        nullable=False,
    )

    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    unlocked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unlock_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PeriodLock {self.period} {self.status}>"