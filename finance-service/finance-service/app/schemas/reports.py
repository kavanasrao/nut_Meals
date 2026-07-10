from pydantic import BaseModel

from app.schemas.ledger import LedgerAccountBalance


class TrialBalanceRow(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    debit_minor: int
    credit_minor: int


class TrialBalanceReport(BaseModel):
    as_of_date: str
    rows: list[TrialBalanceRow]
    total_debit_minor: int
    total_credit_minor: int
    is_balanced: bool


class PnLLineItem(BaseModel):
    account_code: str
    account_name: str
    amount_minor: int


class PnLReport(BaseModel):
    period_start: str
    period_end: str
    granularity: str  # monthly | quarterly | yearly | custom
    income_lines: list[PnLLineItem]
    expense_lines: list[PnLLineItem]
    total_income_minor: int
    total_expense_minor: int
    net_profit_minor: int


class AccountBalancesReport(BaseModel):
    as_of_date: str
    balances: list[LedgerAccountBalance]
