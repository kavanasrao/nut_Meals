"""
Chart of accounts for the double-entry ledger.

Every financial fact in the system is ultimately expressed as debits/credits
against LedgerAccount rows. Accounts are hierarchical (via parent_id) so that
e.g. "Bank - Kotak" and "Bank - HDFC" can roll up into "Assets > Bank".
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class NormalBalance(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


# Accounting rule: assets/expenses are debit-normal; liabilities/equity/income
# are credit-normal. Used to compute signed balances for reports.
ACCOUNT_TYPE_NORMAL_BALANCE = {
    AccountType.ASSET: NormalBalance.DEBIT,
    AccountType.EXPENSE: NormalBalance.DEBIT,
    AccountType.LIABILITY: NormalBalance.CREDIT,
    AccountType.EQUITY: NormalBalance.CREDIT,
    AccountType.INCOME: NormalBalance.CREDIT,
}


class LedgerAccount(TimestampMixin, Base):
    __tablename__ = "ledger_accounts"
    __table_args__ = (
        UniqueConstraint("code", name="uq_ledger_accounts_code"),
        Index("ix_ledger_accounts_type", "account_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "1000", "4000-JUSPAY"
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="account_type_enum", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system_account: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, doc="System accounts cannot be deleted/deactivated via API"
    )

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ledger_accounts.id"), nullable=True
    )
    parent: Mapped["LedgerAccount | None"] = relationship(remote_side="LedgerAccount.id")

    journal_lines: Mapped[list["JournalLine"]] = relationship(back_populates="account")  # noqa: F821

    @property
    def normal_balance(self) -> NormalBalance:
        return ACCOUNT_TYPE_NORMAL_BALANCE[self.account_type]

    def __repr__(self) -> str:
        return f"<LedgerAccount {self.code} {self.name} ({self.account_type})>"
