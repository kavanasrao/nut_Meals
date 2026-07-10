"""Settlement reconciliation endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import FinanceRole, Principal, require_roles
from app.schemas.reconciliation import (
    ReconciliationExceptionOut,
    ReconciliationExceptionResolve,
    ReconciliationRunCreate,
    ReconciliationRunOut,
)
from app.services.reconciliation_service import ReconciliationService
from app.tasks.reconciliation_tasks import run_reconciliation_matching

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


@router.post("/runs", response_model=ReconciliationRunOut, status_code=201)
async def create_reconciliation_run(
    payload: ReconciliationRunCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.RECONCILER)),
):
    """
    Ingests a batch of settlement records (from Juspay/Kotak/etc.) and
    kicks off asynchronous matching via Celery. Returns immediately with
    the created run in PENDING status; poll GET /runs/{id} for progress.
    """
    service = ReconciliationService(db)
    run = await service.start_run(payload, actor=principal.subject)
    run_reconciliation_matching.delay(str(run.id), principal.subject)
    return run


@router.get("/runs/{run_id}", response_model=ReconciliationRunOut)
async def get_reconciliation_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    service = ReconciliationService(db)
    return await service.get_run(run_id)


@router.get("/exceptions", response_model=list[ReconciliationExceptionOut])
async def list_reconciliation_exceptions(
    resolved: bool | None = None,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    service = ReconciliationService(db)
    return await service.list_exceptions(resolved=resolved)


@router.post("/exceptions/{exception_id}/resolve", response_model=ReconciliationExceptionOut)
async def resolve_reconciliation_exception(
    exception_id: uuid.UUID,
    payload: ReconciliationExceptionResolve,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.RECONCILER)),
):
    """Marks a flagged mismatch/unmatched settlement as manually resolved."""
    service = ReconciliationService(db)
    return await service.resolve_exception(exception_id, payload, actor=principal.subject)
