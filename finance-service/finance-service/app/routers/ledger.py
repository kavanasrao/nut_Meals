"""Chart-of-accounts endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import FinanceRole, Principal, require_roles
from app.models.ledger import AccountType
from app.schemas.ledger import LedgerAccountBalance, LedgerAccountCreate, LedgerAccountOut, LedgerAccountUpdate
from app.services.ledger_service import LedgerService

router = APIRouter(prefix="/ledger/accounts", tags=["Ledger Accounts"])


@router.post("", response_model=LedgerAccountOut, status_code=201)
async def create_account(
    payload: LedgerAccountCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.ADMIN)),
):
    """Creates a new ledger account (chart-of-accounts entry). Admin only."""
    service = LedgerService(db)
    return await service.create_account(payload, actor=principal.subject)


@router.get("", response_model=list[LedgerAccountOut])
async def list_accounts(
    account_type: AccountType | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    service = LedgerService(db)
    return await service.list_accounts(account_type=account_type, active_only=active_only)


@router.get("/{account_id}", response_model=LedgerAccountOut)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    service = LedgerService(db)
    return await service.get_account(account_id)


@router.patch("/{account_id}", response_model=LedgerAccountOut)
async def update_account(
    account_id: uuid.UUID,
    payload: LedgerAccountUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.ADMIN)),
):
    service = LedgerService(db)
    return await service.update_account(account_id, payload, actor=principal.subject)


@router.get("/{account_id}/balance", response_model=LedgerAccountBalance)
async def get_account_balance(
    account_id: uuid.UUID,
    as_of_date: str | None = Query(None, description="ISO date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    service = LedgerService(db)
    account = await service.get_account(account_id)
    debit_total, credit_total, balance = await service.get_account_balance(account_id, as_of_date=as_of_date)
    return LedgerAccountBalance(
        account=account, debit_total_minor=debit_total, credit_total_minor=credit_total, balance_minor=balance
    )
