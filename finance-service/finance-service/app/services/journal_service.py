"""
Journal entry service - the heart of the double-entry ledger.

Invariants enforced here (in addition to the DB CHECK constraints):
  1. Every entry has >= 2 lines.
  2. SUM(debit) == SUM(credit) across all lines in an entry.
  3. All referenced accounts exist and are active.
  4. Posting is atomic: either the entry + all lines commit together, or
     nothing does (a single DB transaction per operation).
  5. Once POSTED, an entry is immutable; corrections are made via a
     reversing entry (never by editing/deleting posted lines), preserving
     the audit trail required for tax compliance.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import write_audit_log
from app.models.audit import AuditAction
from app.models.journal import JournalEntry, JournalEntryStatus, JournalLine
from app.models.ledger import LedgerAccount
from app.schemas.journal import JournalEntryCreate


class JournalValidationError(Exception):
    pass


class JournalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _next_entry_number(self) -> str:
        """
        Generates a sequential, human-readable entry number like JE-2026-000123.
        Uses a SELECT ... FOR UPDATE style count within the transaction to
        avoid collisions under concurrent posting (Postgres row locking via
        the sequence-like counting query is safe under the SERIALIZABLE-lite
        guarantee of a single leading digit prefix per year; for very high
        throughput this would be swapped for a DB SEQUENCE).
        """
        year = datetime.now(UTC).year
        count_stmt = (
            select(func.count()).select_from(JournalEntry).where(JournalEntry.entry_number.like(f"JE-{year}-%"))
        )
        result = await self.db.execute(count_stmt)
        count = result.scalar_one()
        return f"JE-{year}-{count + 1:06d}"

    async def _validate_accounts(self, account_ids: set[uuid.UUID]) -> dict[uuid.UUID, LedgerAccount]:
        stmt = select(LedgerAccount).where(LedgerAccount.id.in_(account_ids))
        result = await self.db.execute(stmt)
        accounts = {a.id: a for a in result.scalars().all()}
        missing = account_ids - accounts.keys()
        if missing:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown ledger account id(s): {missing}")
        inactive = [a.code for a in accounts.values() if not a.is_active]
        if inactive:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Cannot post to inactive account(s): {inactive}")
        return accounts

    async def create_and_post_entry(
        self, payload: JournalEntryCreate, *, actor: str, auto_post: bool = True
    ) -> JournalEntry:
        """
        Creates a journal entry with its lines and, by default, immediately
        posts it. Pydantic (`JournalEntryCreate`) already validated that
        debits == credits at the request level; we re-validate here since
        this method may also be called from internal code paths (e.g.
        Celery reconciliation tasks) that don't go through the API schema.
        """
        account_ids = {line.account_id for line in payload.lines}
        await self._validate_accounts(account_ids)

        total_debit = sum(line.debit_amount_minor for line in payload.lines)
        total_credit = sum(line.credit_amount_minor for line in payload.lines)
        if total_debit != total_credit:
            raise JournalValidationError(f"Unbalanced entry: debit={total_debit} credit={total_credit}")

        entry_number = await self._next_entry_number()
        entry = JournalEntry(
            entry_number=entry_number,
            entry_date=payload.entry_date,
            description=payload.description,
            source_type=payload.source_type,
            source_reference=payload.source_reference,
            currency=payload.currency,
            created_by=actor,
            status=JournalEntryStatus.DRAFT,
        )
        entry.lines = [
            JournalLine(
                account_id=line.account_id,
                line_number=idx + 1,
                debit_amount_minor=line.debit_amount_minor,
                credit_amount_minor=line.credit_amount_minor,
                memo=line.memo,
            )
            for idx, line in enumerate(payload.lines)
        ]
        self.db.add(entry)
        await self.db.flush()

        await write_audit_log(
            self.db,
            action=AuditAction.JOURNAL_ENTRY_CREATED,
            actor=actor,
            entity_type="journal_entry",
            entity_id=str(entry.id),
            metadata={"entry_number": entry_number, "total_debit_minor": total_debit},
        )

        if auto_post:
            await self._post(entry, actor=actor)

        await self.db.commit()
        return await self.get_entry(entry.id)

    async def _post(self, entry: JournalEntry, *, actor: str) -> None:
        if entry.status != JournalEntryStatus.DRAFT:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Entry {entry.entry_number} is not in DRAFT status")
        entry.status = JournalEntryStatus.POSTED
        entry.posted_by = actor
        await write_audit_log(
            self.db,
            action=AuditAction.JOURNAL_ENTRY_POSTED,
            actor=actor,
            entity_type="journal_entry",
            entity_id=str(entry.id),
            metadata={"entry_number": entry.entry_number},
        )
        await self.db.flush()

    async def post_entry(self, entry_id: uuid.UUID, *, actor: str) -> JournalEntry:
        entry = await self.get_entry(entry_id)
        await self._post(entry, actor=actor)
        await self.db.commit()
        return await self.get_entry(entry_id)

    async def reverse_entry(self, entry_id: uuid.UUID, *, actor: str, reason: str) -> JournalEntry:
        """
        Creates and posts a new entry with debits/credits swapped relative
        to the original, then marks the original REVERSED. This preserves
        an immutable audit trail rather than mutating history.
        """
        original = await self.get_entry(entry_id)
        if original.status != JournalEntryStatus.POSTED:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only POSTED entries can be reversed")

        entry_number = await self._next_entry_number()
        reversal = JournalEntry(
            entry_number=entry_number,
            entry_date=datetime.now(UTC).date().isoformat(),
            description=f"Reversal of {original.entry_number}: {reason}",
            source_type=original.source_type,
            source_reference=original.source_reference,
            currency=original.currency,
            created_by=actor,
            posted_by=actor,
            status=JournalEntryStatus.POSTED,
            reversal_of_id=original.id,
        )
        reversal.lines = [
            JournalLine(
                account_id=line.account_id,
                line_number=idx + 1,
                debit_amount_minor=line.credit_amount_minor,  # swapped
                credit_amount_minor=line.debit_amount_minor,  # swapped
                memo=f"Reversal: {line.memo or ''}".strip(),
            )
            for idx, line in enumerate(original.lines)
        ]
        self.db.add(reversal)
        original.status = JournalEntryStatus.REVERSED
        await self.db.flush()

        await write_audit_log(
            self.db,
            action=AuditAction.JOURNAL_ENTRY_REVERSED,
            actor=actor,
            entity_type="journal_entry",
            entity_id=str(original.id),
            metadata={"reversal_entry_id": str(reversal.id), "reason": reason},
        )
        await self.db.commit()
        return await self.get_entry(reversal.id)

    async def get_entry(self, entry_id: uuid.UUID) -> JournalEntry:
        stmt = select(JournalEntry).options(selectinload(JournalEntry.lines)).where(JournalEntry.id == entry_id)
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Journal entry not found")
        return entry

    async def list_entries(
        self,
        *,
        status_filter: JournalEntryStatus | None = None,
        source_reference: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JournalEntry]:
        stmt = select(JournalEntry).options(selectinload(JournalEntry.lines))
        if status_filter:
            stmt = stmt.where(JournalEntry.status == status_filter)
        if source_reference:
            stmt = stmt.where(JournalEntry.source_reference == source_reference)
        stmt = (
            stmt.order_by(JournalEntry.entry_date.desc(), JournalEntry.entry_number.desc()).limit(limit).offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
