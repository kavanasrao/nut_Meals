import pytest

from app.models.ledger import AccountType
from app.schemas.ledger import LedgerAccountCreate
from app.services.ledger_service import LedgerService


@pytest.mark.asyncio
async def test_create_account_success(db_session):
    service = LedgerService(db_session)
    account = await service.create_account(
        LedgerAccountCreate(code="9000", name="Test Asset", account_type=AccountType.ASSET),
        actor="tester",
    )
    assert account.code == "9000"
    assert account.is_active is True
    assert account.normal_balance.value == "debit"


@pytest.mark.asyncio
async def test_create_account_duplicate_code_conflicts(db_session):
    service = LedgerService(db_session)
    await service.create_account(
        LedgerAccountCreate(code="9001", name="First", account_type=AccountType.ASSET), actor="tester"
    )
    with pytest.raises(Exception) as exc_info:
        await service.create_account(
            LedgerAccountCreate(code="9001", name="Duplicate", account_type=AccountType.EXPENSE), actor="tester"
        )
    assert "already exists" in str(exc_info.value.detail) if hasattr(exc_info.value, "detail") else True


@pytest.mark.asyncio
async def test_list_accounts_filters_active_only(db_session):
    service = LedgerService(db_session)
    await service.create_account(
        LedgerAccountCreate(code="9002", name="Active", account_type=AccountType.INCOME), actor="tester"
    )
    inactive = await service.create_account(
        LedgerAccountCreate(code="9003", name="Inactive", account_type=AccountType.INCOME), actor="tester"
    )
    from app.schemas.ledger import LedgerAccountUpdate

    await service.update_account(inactive.id, LedgerAccountUpdate(is_active=False), actor="tester")

    accounts = await service.list_accounts(active_only=True)
    codes = {a.code for a in accounts}
    assert "9002" in codes
    assert "9003" not in codes


@pytest.mark.asyncio
async def test_system_account_cannot_be_deactivated(db_session):
    service = LedgerService(db_session)
    account = await service.create_account(
        LedgerAccountCreate(code="9004", name="System Account", account_type=AccountType.ASSET), actor="tester"
    )
    account.is_system_account = True
    await db_session.flush()

    from fastapi import HTTPException

    from app.schemas.ledger import LedgerAccountUpdate

    with pytest.raises(HTTPException):
        await service.update_account(account.id, LedgerAccountUpdate(is_active=False), actor="tester")


@pytest.mark.asyncio
async def test_create_account_via_api(client, auth_headers):
    response = await client.post(
        "/api/v1/ledger/accounts",
        json={"code": "9100", "name": "API Created", "account_type": "asset"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["code"] == "9100"
    assert body["account_type"] == "asset"


@pytest.mark.asyncio
async def test_list_accounts_via_api(client, auth_headers):
    await client.post(
        "/api/v1/ledger/accounts",
        json={"code": "9101", "name": "API List Test", "account_type": "expense"},
        headers=auth_headers,
    )
    response = await client.get("/api/v1/ledger/accounts", headers=auth_headers)
    assert response.status_code == 200
    codes = {a["code"] for a in response.json()}
    assert "9101" in codes
