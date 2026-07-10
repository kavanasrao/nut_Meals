"""
API routes for Analytics: KPI dashboards (conversion rate, churn, repeat
customers, GMV/AOV) built from nightly Celery aggregation snapshots.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AdminPrincipal, require_roles
from app.database import get_db
from app.models.common import AdminRole
from app.schemas.analytics import KPISummaryResponse, KPITrendResponse
from app.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_READ_ROLES = (AdminRole.SUPER_ADMIN, AdminRole.ANALYTICS_VIEWER, AdminRole.FINANCE_ADMIN)


@router.get("/kpis/summary", response_model=KPISummaryResponse)
async def get_kpi_summary(
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_READ_ROLES)),
) -> KPISummaryResponse:
    """Latest-day KPI snapshot plus day-over-day deltas, for headline dashboard cards."""
    summary = await analytics_service.get_kpi_summary(db)
    return KPISummaryResponse(**summary)


@router.get("/kpis/trend", response_model=KPITrendResponse)
async def get_kpi_trend(
    period_start: date | None = None,
    period_end: date | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_READ_ROLES)),
) -> KPITrendResponse:
    """Time-series of daily KPI snapshots for charting. Defaults to the last 30 days."""
    period_end = period_end or date.today()
    period_start = period_start or (period_end - timedelta(days=30))

    if period_end < period_start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="period_end must be >= period_start")

    snapshots = await analytics_service.get_kpi_trend(db, period_start=period_start, period_end=period_end)
    return KPITrendResponse(snapshots=snapshots, period_start=period_start, period_end=period_end)
