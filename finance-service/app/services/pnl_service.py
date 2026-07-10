"""Profit & Loss (Income Statement) report generation."""

import calendar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import JournalEntry, JournalEntryStatus, JournalLine
from app.models.ledger import AccountType, LedgerAccount
from app.schemas.reports import PnLLineItem, PnLReport


def resolve_period(*, year: int, granularity: str, period_index: int | None) -> tuple[str, str]:
    """
    Resolves a (year, granularity, period_index) tuple into ISO date bounds.
    granularity: 'monthly' (period_index=1-12), 'quarterly' (1-4), 'yearly' (ignored).
    """
    if granularity == "yearly":
        return f"{year}-01-01", f"{year}-12-31"

    if granularity == "monthly":
        if not period_index or not (1 <= period_index <= 12):
            raise ValueError("monthly granularity requires period_index 1-12")
        last_day = calendar.monthrange(year, period_index)[1]
        return f"{year}-{period_index:02d}-01", f"{year}-{period_index:02d}-{last_day:02d}"

    if granularity == "quarterly":
        if not period_index or not (1 <= period_index <= 4):
            raise ValueError("quarterly granularity requires period_index 1-4")
        start_month = (period_index - 1) * 3 + 1
        end_month = start_month + 2
        last_day = calendar.monthrange(year, end_month)[1]
        return f"{year}-{start_month:02d}-01", f"{year}-{end_month:02d}-{last_day:02d}"

    raise ValueError(f"Unknown granularity: {granularity}")


class PnLService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, *, period_start: str, period_end: str, granularity: str = "custom") -> PnLReport:
        income_lines = await self._lines_for_type(AccountType.INCOME, period_start, period_end)
        expense_lines = await self._lines_for_type(AccountType.EXPENSE, period_start, period_end)

        total_income = sum(line.amount_minor for line in income_lines)
        total_expense = sum(line.amount_minor for line in expense_lines)

        return PnLReport(
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
            income_lines=income_lines,
            expense_lines=expense_lines,
            total_income_minor=total_income,
            total_expense_minor=total_expense,
            net_profit_minor=total_income - total_expense,
        )

    async def _lines_for_type(self, account_type: AccountType, period_start: str, period_end: str) -> list[PnLLineItem]:
        # Income/expense accounts are credit-/debit-normal respectively;
        # net activity in the period is what matters for P&L (not cumulative balance).
        stmt = (
            select(
                LedgerAccount.code,
                LedgerAccount.name,
                func.coalesce(func.sum(JournalLine.credit_amount_minor - JournalLine.debit_amount_minor), 0).label(
                    "net"
                ),
            )
            .join(JournalLine, JournalLine.account_id == LedgerAccount.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(LedgerAccount.account_type == account_type)
            .where(JournalEntry.status == JournalEntryStatus.POSTED)
            .where(JournalEntry.entry_date >= period_start)
            .where(JournalEntry.entry_date <= period_end)
            .group_by(LedgerAccount.id, LedgerAccount.code, LedgerAccount.name)
            .having(func.sum(JournalLine.credit_amount_minor - JournalLine.debit_amount_minor) != 0)
            .order_by(LedgerAccount.code)
        )
        result = await self.db.execute(stmt)

        lines = []
        for code, name, net in result.all():
            # For EXPENSE accounts (debit-normal) we want a positive "amount spent",
            # so flip the sign of the credit-minus-debit net.
            amount = int(net) if account_type == AccountType.INCOME else -int(net)
            lines.append(PnLLineItem(account_code=code, account_name=name, amount_minor=amount))
        return lines
