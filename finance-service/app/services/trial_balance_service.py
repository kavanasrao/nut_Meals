"""Trial balance report generation."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import JournalEntry, JournalEntryStatus, JournalLine
from app.models.ledger import LedgerAccount
from app.schemas.reports import TrialBalanceReport, TrialBalanceRow


class TrialBalanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, *, as_of_date: str) -> TrialBalanceReport:
        """
        For each account, sums posted debits/credits up to and including
        `as_of_date`, then presents the account's *net* balance on the
        correct side (debit-normal accounts show a debit balance, and vice
        versa), which is the standard trial balance presentation.
        """
        stmt = (
            select(
                LedgerAccount.code,
                LedgerAccount.name,
                LedgerAccount.account_type,
                func.coalesce(func.sum(JournalLine.debit_amount_minor), 0).label("debit_total"),
                func.coalesce(func.sum(JournalLine.credit_amount_minor), 0).label("credit_total"),
            )
            .join(JournalLine, JournalLine.account_id == LedgerAccount.id, isouter=True)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id, isouter=True)
            .where(
                (JournalEntry.id.is_(None))
                | ((JournalEntry.status == JournalEntryStatus.POSTED) & (JournalEntry.entry_date <= as_of_date))
            )
            .where(LedgerAccount.is_active.is_(True))
            .group_by(LedgerAccount.id, LedgerAccount.code, LedgerAccount.name, LedgerAccount.account_type)
            .order_by(LedgerAccount.code)
        )
        result = await self.db.execute(stmt)

        rows: list[TrialBalanceRow] = []
        total_debit = 0
        total_credit = 0

        from app.models.ledger import ACCOUNT_TYPE_NORMAL_BALANCE  # noqa: F401  (kept for readability/doc purposes)

        for code, name, account_type, debit_total, credit_total in result.all():
            debit_total, credit_total = int(debit_total), int(credit_total)
            net = debit_total - credit_total
            # Trial balance presentation: net debit activity shows in the debit column,
            # net credit activity shows in the credit column - regardless of the account's
            # normal balance side. (Normal balance matters for P&L sign, not trial balance display.)
            row_debit, row_credit = max(net, 0), max(-net, 0)

            if row_debit == 0 and row_credit == 0:
                continue

            rows.append(
                TrialBalanceRow(
                    account_code=code,
                    account_name=name,
                    account_type=account_type.value,
                    debit_minor=row_debit,
                    credit_minor=row_credit,
                )
            )
            total_debit += row_debit
            total_credit += row_credit

        return TrialBalanceReport(
            as_of_date=as_of_date,
            rows=rows,
            total_debit_minor=total_debit,
            total_credit_minor=total_credit,
            is_balanced=(total_debit == total_credit),
        )
