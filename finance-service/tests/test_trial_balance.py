import pytest

from app.models.ledger import AccountType
from app.schemas.journal import JournalEntryCreate, JournalLineIn
from app.schemas.ledger import LedgerAccountCreate
from app.services.journal_service import JournalService
from app.services.ledger_service import LedgerService
from app.services.trial_balance_service import TrialBalanceService


@pytest.mark.asyncio
async def test_trial_balance_is_balanced_after_postings(db_session):
    ledger = LedgerService(db_session)
    journal = JournalService(db_session)

    bank = await ledger.create_account(
        LedgerAccountCreate(code="TBB1", name="TB Bank", account_type=AccountType.ASSET), actor="tester"
    )
    revenue = await ledger.create_account(
        LedgerAccountCreate(code="TBB2", name="TB Revenue", account_type=AccountType.INCOME), actor="tester"
    )

    await journal.create_and_post_entry(
        JournalEntryCreate(
            entry_date="2026-07-10",
            description="Sale 1",
            source_type="order",
            source_reference="TB-ORDER-1",
            lines=[
                JournalLineIn(account_id=bank.id, debit_amount_minor=30000),
                JournalLineIn(account_id=revenue.id, credit_amount_minor=30000),
            ],
        ),
        actor="tester",
    )

    tb_service = TrialBalanceService(db_session)
    report = await tb_service.generate(as_of_date="2026-07-10")

    assert report.is_balanced is True
    assert report.total_debit_minor == report.total_credit_minor

    bank_row = next(r for r in report.rows if r.account_code == "TBB1")
    revenue_row = next(r for r in report.rows if r.account_code == "TBB2")
    assert bank_row.debit_minor == 30000
    assert revenue_row.credit_minor == 30000


@pytest.mark.asyncio
async def test_trial_balance_excludes_future_dated_entries(db_session):
    ledger = LedgerService(db_session)
    journal = JournalService(db_session)

    bank = await ledger.create_account(
        LedgerAccountCreate(code="TBB3", name="TB Bank Future", account_type=AccountType.ASSET), actor="tester"
    )
    revenue = await ledger.create_account(
        LedgerAccountCreate(code="TBB4", name="TB Revenue Future", account_type=AccountType.INCOME), actor="tester"
    )

    await journal.create_and_post_entry(
        JournalEntryCreate(
            entry_date="2099-01-01",
            description="Future sale",
            source_type="order",
            source_reference="TB-ORDER-FUTURE",
            lines=[
                JournalLineIn(account_id=bank.id, debit_amount_minor=5000),
                JournalLineIn(account_id=revenue.id, credit_amount_minor=5000),
            ],
        ),
        actor="tester",
    )

    tb_service = TrialBalanceService(db_session)
    report = await tb_service.generate(as_of_date="2026-07-10")
    codes_with_balance = {r.account_code for r in report.rows}
    assert "TBB3" not in codes_with_balance
    assert "TBB4" not in codes_with_balance


@pytest.mark.asyncio
async def test_trial_balance_via_api(client, auth_headers):
    response = await client.get("/api/v1/reports/trial-balance?as_of_date=2026-07-10", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["is_balanced"] is True
    assert body["total_debit_minor"] == body["total_credit_minor"]
