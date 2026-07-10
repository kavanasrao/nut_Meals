import pytest

from app.models.ledger import AccountType
from app.schemas.journal import JournalEntryCreate, JournalLineIn
from app.schemas.ledger import LedgerAccountCreate
from app.services.journal_service import JournalService
from app.services.ledger_service import LedgerService
from app.services.pnl_service import PnLService, resolve_period


def test_resolve_period_monthly():
    start, end = resolve_period(year=2026, granularity="monthly", period_index=2)
    assert start == "2026-02-01"
    assert end == "2026-02-28"


def test_resolve_period_quarterly():
    start, end = resolve_period(year=2026, granularity="quarterly", period_index=1)
    assert start == "2026-01-01"
    assert end == "2026-03-31"


def test_resolve_period_yearly():
    start, end = resolve_period(year=2026, granularity="yearly", period_index=None)
    assert start == "2026-01-01"
    assert end == "2026-12-31"


def test_resolve_period_rejects_invalid_month():
    with pytest.raises(ValueError):
        resolve_period(year=2026, granularity="monthly", period_index=13)


@pytest.mark.asyncio
async def test_pnl_computes_net_profit(db_session):
    ledger = LedgerService(db_session)
    journal = JournalService(db_session)

    bank = await ledger.create_account(
        LedgerAccountCreate(code="PL_BANK", name="PL Bank", account_type=AccountType.ASSET), actor="tester"
    )
    revenue = await ledger.create_account(
        LedgerAccountCreate(code="PL_REV", name="PL Revenue", account_type=AccountType.INCOME), actor="tester"
    )
    expense = await ledger.create_account(
        LedgerAccountCreate(code="PL_EXP", name="PL Expense", account_type=AccountType.EXPENSE), actor="tester"
    )

    await journal.create_and_post_entry(
        JournalEntryCreate(
            entry_date="2026-03-15",
            description="Revenue booking",
            source_type="order",
            source_reference="PL-ORDER-1",
            lines=[
                JournalLineIn(account_id=bank.id, debit_amount_minor=100000),
                JournalLineIn(account_id=revenue.id, credit_amount_minor=100000),
            ],
        ),
        actor="tester",
    )
    await journal.create_and_post_entry(
        JournalEntryCreate(
            entry_date="2026-03-20",
            description="Expense booking",
            source_type="manual_adjustment",
            source_reference="PL-EXPENSE-1",
            lines=[
                JournalLineIn(account_id=expense.id, debit_amount_minor=40000),
                JournalLineIn(account_id=bank.id, credit_amount_minor=40000),
            ],
        ),
        actor="tester",
    )

    pnl_service = PnLService(db_session)
    report = await pnl_service.generate(period_start="2026-03-01", period_end="2026-03-31", granularity="monthly")

    assert report.total_income_minor == 100000
    assert report.total_expense_minor == 40000
    assert report.net_profit_minor == 60000


@pytest.mark.asyncio
async def test_pnl_via_api_monthly(client, auth_headers):
    response = await client.get(
        "/api/v1/reports/pnl?year=2026&granularity=monthly&period_index=3", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["period_start"] == "2026-03-01"
    assert body["period_end"] == "2026-03-31"


@pytest.mark.asyncio
async def test_pnl_via_api_rejects_missing_period_index(client, auth_headers):
    response = await client.get("/api/v1/reports/pnl?year=2026&granularity=monthly", headers=auth_headers)
    assert response.status_code == 400
