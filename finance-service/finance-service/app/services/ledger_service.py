"""Service layer for chart-of-accounts management and balance queries."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.models.audit import AuditAction
from app.models.journal import JournalEntry, JournalEntryStatus, JournalLine
from app.models.ledger import LedgerAccount, NormalBalance
from app.schemas.ledger import LedgerAccountCreate, LedgerAccountUpdate


class LedgerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_account(self, payload: LedgerAccountCreate, *, actor: str) -> LedgerAccount:
        account = LedgerAccount(
            code=payload.code,
            name=payload.name,
            account_type=payload.account_type,
            description=payload.description,
            parent_id=payload.parent_id,
        )
        self.db.add(account)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, f"Account code '{payload.code}' already exists") from exc

        await write_audit_log(
            self.db,
            action=AuditAction.LEDGER_ACCOUNT_CREATED,
            actor=actor,
            entity_type="ledger_account",
            entity_id=str(account.id),
            metadata={"code": account.code, "account_type": account.account_type.value},
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def update_account(self, account_id: uuid.UUID, payload: LedgerAccountUpdate, *, actor: str) -> LedgerAccount:
        account = await self.get_account(account_id)
        if account.is_system_account and payload.is_active is False:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "System accounts cannot be deactivated")

        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(account, field, value)

        await write_audit_log(
            self.db,
            action=AuditAction.LEDGER_ACCOUNT_UPDATED,
            actor=actor,
            entity_type="ledger_account",
            entity_id=str(account.id),
            metadata={"changes": changes},
        )
        await self.db.commit()
        await self.db.refresh(account)
        return account

    async def get_account(self, account_id: uuid.UUID) -> LedgerAccount:
        account = await self.db.get(LedgerAccount, account_id)
        if account is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ledger account not found")
        return account

    async def list_accounts(self, *, account_type: str | None = None, active_only: bool = True) -> list[LedgerAccount]:
        stmt = select(LedgerAccount)
        if account_type:
            stmt = stmt.where(LedgerAccount.account_type == account_type)
        if active_only:
            stmt = stmt.where(LedgerAccount.is_active.is_(True))
        stmt = stmt.order_by(LedgerAccount.code)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_account_balance(
        self, account_id: uuid.UUID, *, as_of_date: str | None = None
    ) -> tuple[int, int, int]:
        """
        Returns (debit_total_minor, credit_total_minor, signed_balance_minor).
        Only POSTED journal entries count towards balances.
        """
        account = await self.get_account(account_id)
        stmt = (
            select(
                func.coalesce(func.sum(JournalLine.debit_amount_minor), 0),
                func.coalesce(func.sum(JournalLine.credit_amount_minor), 0),
            )
            .join(JournalEntry, JournalLine.journal_entry_id == JournalEntry.id)
            .where(JournalLine.account_id == account_id)
            .where(JournalEntry.status == JournalEntryStatus.POSTED)
        )
        if as_of_date:
            stmt = stmt.where(JournalEntry.entry_date <= as_of_date)

        result = await self.db.execute(stmt)
        debit_total, credit_total = result.one()

        if account.normal_balance == NormalBalance.DEBIT:
            balance = debit_total - credit_total
        else:
            balance = credit_total - debit_total

        return int(debit_total), int(credit_total), int(balance)
