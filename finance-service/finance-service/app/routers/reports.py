"""Trial balance and Profit & Loss report endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import FinanceRole, Principal, require_roles
from app.schemas.reports import PnLReport, TrialBalanceReport
from app.services.pnl_service import PnLService, resolve_period
from app.services.trial_balance_service import TrialBalanceService

router = APIRouter(tags=["Reports"])


@router.get("/reports/trial-balance", response_model=TrialBalanceReport)
async def get_trial_balance(
    as_of_date: str = Query(default_factory=lambda: date.today().isoformat(), description="ISO date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    """Generates a trial balance as of the given date from all POSTED journal entries."""
    service = TrialBalanceService(db)
    return await service.generate(as_of_date=as_of_date)


@router.get("/reports/pnl", response_model=PnLReport)
async def get_pnl_report(
    year: int = Query(..., ge=2000, le=2100),
    granularity: str = Query("monthly", pattern="^(monthly|quarterly|yearly)$"),
    period_index: int | None = Query(None, description="Month (1-12) or quarter (1-4); ignored for yearly"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    """Generates a Profit & Loss report for the requested monthly/quarterly/yearly period."""
    try:
        period_start, period_end = resolve_period(year=year, granularity=granularity, period_index=period_index)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    service = PnLService(db)
    return await service.generate(period_start=period_start, period_end=period_end, granularity=granularity)


@router.get("/reports/pnl/custom", response_model=PnLReport)
async def get_pnl_custom_range(
    period_start: str = Query(..., description="ISO date YYYY-MM-DD"),
    period_end: str = Query(..., description="ISO date YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles(FinanceRole.VIEWER)),
):
    """Generates a P&L report for an arbitrary custom date range."""
    if period_start > period_end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "period_start must be <= period_end")
    service = PnLService(db)
    return await service.generate(period_start=period_start, period_end=period_end, granularity="custom")
