import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.ledger import AccountType
from app.schemas.journal import JournalEntryCreate, JournalLineIn
from app.schemas.ledger import LedgerAccountCreate
from app.services.journal_service import JournalService
from app.services.ledger_service import LedgerService


async def _make_accounts(db_session):
    ledger = LedgerService(db_session)
    bank = await ledger.create_account(
        LedgerAccountCreate(code="TB100", name="Test Bank", account_type=AccountType.ASSET), actor="tester"
    )
    revenue = await ledger.create_account(
        LedgerAccountCreate(code="TB400", name="Test Revenue", account_type=AccountType.INCOME), actor="tester"
    )
    return bank, revenue


def test_journal_line_must_be_single_sided():
    with pytest.raises(ValidationError):
        JournalLineIn(
            account_id="00000000-0000-0000-0000-000000000000", debit_amount_minor=100, credit_amount_minor=100
        )

    with pytest.raises(ValidationError):
        JournalLineIn(account_id="00000000-0000-0000-0000-000000000000", debit_amount_minor=0, credit_amount_minor=0)


def test_journal_entry_rejects_unbalanced_lines():
    with pytest.raises(ValidationError, match="Unbalanced entry"):
        JournalEntryCreate(
            entry_date="2026-07-10",
            description="test",
            source_type="manual_adjustment",
            source_reference="ref-1",
            lines=[
                JournalLineIn(account_id="00000000-0000-0000-0000-000000000000", debit_amount_minor=100),
                JournalLineIn(account_id="00000000-0000-0000-0000-000000000001", credit_amount_minor=50),
            ],
        )


def test_journal_entry_requires_at_least_two_lines():
    with pytest.raises(ValidationError):
        JournalEntryCreate(
            entry_date="2026-07-10",
            description="test",
            source_type="manual_adjustment",
            source_reference="ref-1",
            lines=[JournalLineIn(account_id="00000000-0000-0000-0000-000000000000", debit_amount_minor=100)],
        )


@pytest.mark.asyncio
async def test_create_and_post_balanced_entry(db_session):
    bank, revenue = await _make_accounts(db_session)
    service = JournalService(db_session)

    payload = JournalEntryCreate(
        entry_date="2026-07-10",
        description="Test sale",
        source_type="order",
        source_reference="ORDER-1",
        lines=[
            JournalLineIn(account_id=bank.id, debit_amount_minor=50000),
            JournalLineIn(account_id=revenue.id, credit_amount_minor=50000),
        ],
    )
    entry = await service.create_and_post_entry(payload, actor="tester")
    assert entry.status.value == "posted"
    assert entry.entry_number.startswith("JE-")
    assert len(entry.lines) == 2
    assert sum(ln.debit_amount_minor for ln in entry.lines) == sum(ln.credit_amount_minor for ln in entry.lines)


@pytest.mark.asyncio
async def test_post_rejects_unknown_account(db_session):
    service = JournalService(db_session)
    payload = JournalEntryCreate(
        entry_date="2026-07-10",
        description="Bad entry",
        source_type="manual_adjustment",
        source_reference="ref-bad",
        lines=[
            JournalLineIn(account_id="11111111-1111-1111-1111-111111111111", debit_amount_minor=100),
            JournalLineIn(account_id="22222222-2222-2222-2222-222222222222", credit_amount_minor=100),
        ],
    )
    with pytest.raises(HTTPException):
        await service.create_and_post_entry(payload, actor="tester")


@pytest.mark.asyncio
async def test_reverse_entry_creates_offsetting_entry(db_session):
    bank, revenue = await _make_accounts(db_session)
    service = JournalService(db_session)

    payload = JournalEntryCreate(
        entry_date="2026-07-10",
        description="Original sale",
        source_type="order",
        source_reference="ORDER-2",
        lines=[
            JournalLineIn(account_id=bank.id, debit_amount_minor=20000),
            JournalLineIn(account_id=revenue.id, credit_amount_minor=20000),
        ],
    )
    original = await service.create_and_post_entry(payload, actor="tester")
    reversal = await service.reverse_entry(original.id, actor="tester", reason="duplicate booking")

    refreshed_original = await service.get_entry(original.id)
    assert refreshed_original.status.value == "reversed"
    assert reversal.reversal_of_id == original.id

    bank_line = next(line for line in reversal.lines if line.account_id == bank.id)
    revenue_line = next(line for line in reversal.lines if line.account_id == revenue.id)
    assert bank_line.credit_amount_minor == 20000  # was debit in original
    assert revenue_line.debit_amount_minor == 20000  # was credit in original


@pytest.mark.asyncio
async def test_cannot_reverse_a_draft_entry(db_session):
    bank, revenue = await _make_accounts(db_session)
    service = JournalService(db_session)

    payload = JournalEntryCreate(
        entry_date="2026-07-10",
        description="Draft entry",
        source_type="order",
        source_reference="ORDER-3",
        lines=[
            JournalLineIn(account_id=bank.id, debit_amount_minor=1000),
            JournalLineIn(account_id=revenue.id, credit_amount_minor=1000),
        ],
    )
    draft = await service.create_and_post_entry(payload, actor="tester", auto_post=False)
    assert draft.status.value == "draft"

    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await service.reverse_entry(draft.id, actor="tester", reason="oops")


@pytest.mark.asyncio
async def test_create_journal_entry_via_api(client, auth_headers):
    account_resp1 = await client.post(
        "/api/v1/ledger/accounts",
        json={"code": "API_BANK", "name": "API Bank", "account_type": "asset"},
        headers=auth_headers,
    )
    account_resp2 = await client.post(
        "/api/v1/ledger/accounts",
        json={"code": "API_REV", "name": "API Revenue", "account_type": "income"},
        headers=auth_headers,
    )
    bank_id = account_resp1.json()["id"]
    revenue_id = account_resp2.json()["id"]

    response = await client.post(
        "/api/v1/journal/entries",
        json={
            "entry_date": "2026-07-10",
            "description": "API order",
            "source_type": "order",
            "source_reference": "ORDER-API-1",
            "lines": [
                {"account_id": bank_id, "debit_amount_minor": 1500},
                {"account_id": revenue_id, "credit_amount_minor": 1500},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "posted"


@pytest.mark.asyncio
async def test_create_journal_entry_via_api_rejects_unbalanced(client, auth_headers):
    account_resp = await client.post(
        "/api/v1/ledger/accounts",
        json={"code": "API_BANK2", "name": "API Bank 2", "account_type": "asset"},
        headers=auth_headers,
    )
    bank_id = account_resp.json()["id"]

    response = await client.post(
        "/api/v1/journal/entries",
        json={
            "entry_date": "2026-07-10",
            "description": "Bad API order",
            "source_type": "order",
            "source_reference": "ORDER-API-2",
            "lines": [
                {"account_id": bank_id, "debit_amount_minor": 1500},
                {"account_id": bank_id, "credit_amount_minor": 1000},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
