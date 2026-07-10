"""
Journal entries: the atomic unit of the double-entry ledger.

A JournalEntry groups two or more JournalLine rows. The invariant enforced
both in application logic (JournalService) and via a DB CHECK/trigger is:

    SUM(debit_amount) == SUM(credit_amount)  for all lines in an entry

Amounts are stored as BigInteger in the smallest currency unit (paise for
INR) to avoid floating point rounding errors in accounting data.
"""

import enum
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class JournalEntryStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class JournalSourceType(str, enum.Enum):
    ORDER = "order"
    REFUND = "refund"
    SETTLEMENT = "settlement"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    RECONCILIATION = "reconciliation"


class JournalEntry(TimestampMixin, Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_entries_status", "status"),
        Index("ix_journal_entries_source", "source_type", "source_reference"),
        Index("ix_journal_entries_entry_date", "entry_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    entry_date: Mapped[str] = mapped_column(
        String(10), nullable=False, doc="ISO date YYYY-MM-DD of the accounting period this entry belongs to"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[JournalEntryStatus] = mapped_column(
        Enum(JournalEntryStatus, name="journal_entry_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=JournalEntryStatus.DRAFT,
        nullable=False,
    )
    source_type: Mapped[JournalSourceType] = mapped_column(
        Enum(JournalSourceType, name="journal_source_type_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    source_reference: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="Order ID / settlement batch ID / etc. from the originating domain"
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)

    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="User/service principal that created the entry"
    )
    posted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True
    )

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="JournalLine.line_number"
    )

    def __repr__(self) -> str:
        return f"<JournalEntry {self.entry_number} {self.status}>"


class JournalLine(TimestampMixin, Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        CheckConstraint(
            "(debit_amount_minor > 0 AND credit_amount_minor = 0) OR "
            "(credit_amount_minor > 0 AND debit_amount_minor = 0)",
            name="ck_journal_line_single_sided",
        ),
        CheckConstraint("debit_amount_minor >= 0 AND credit_amount_minor >= 0", name="ck_journal_line_non_negative"),
        Index("ix_journal_lines_entry", "journal_entry_id"),
        Index("ix_journal_lines_account", "account_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ledger_accounts.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    debit_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    credit_amount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    account: Mapped["LedgerAccount"] = relationship(back_populates="journal_lines")  # noqa: F821

    def __repr__(self) -> str:
        return f"<JournalLine dr={self.debit_amount_minor} cr={self.credit_amount_minor}>"
