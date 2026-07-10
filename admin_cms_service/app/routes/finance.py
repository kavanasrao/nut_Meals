"""
API routes for Finance Dashboards: revenue/expense/P&L summaries and
exportable reports, aggregated from the Finance service.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit_event
from app.core.security import AdminPrincipal, require_roles
from app.database import get_db
from app.models.common import AdminRole
from app.schemas.finance import (
    FinanceReportRequest,
    FinanceReportResponse,
    FinanceSummaryResponse,
)
from app.services import finance_service
from app.services.finance_client import FinanceServiceClient, get_finance_client
from app.tasks.finance_tasks import generate_finance_report_task

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])

_FINANCE_ROLES = (AdminRole.SUPER_ADMIN, AdminRole.FINANCE_ADMIN)


@router.get("/summary", response_model=FinanceSummaryResponse)
async def get_finance_summary(
    period_start: date,
    period_end: date,
    granularity: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    force_refresh: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_FINANCE_ROLES)),
    finance_client: FinanceServiceClient = Depends(get_finance_client),
) -> FinanceSummaryResponse:
    """
    Revenue/expense/P&L summary for a period. Served from cache unless
    `force_refresh=true` or no cache entry exists yet.
    """
    if period_end < period_start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="period_end must be >= period_start")

    cached = None if force_refresh else await finance_service.get_cached_summary(
        db, period_start=period_start, period_end=period_end, granularity=granularity
    )

    if cached is None:
        cached = await finance_service.refresh_finance_summary(
            db,
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
            finance_client=finance_client,
        )
        await db.commit()

    return FinanceSummaryResponse.model_validate(cached)


@router.post("/reports", response_model=FinanceReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_finance_report(
    payload: FinanceReportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_FINANCE_ROLES)),
) -> FinanceReportResponse:
    """
    Request an exportable finance report (CSV/PDF/XLSX). Returns
    immediately with status=pending; the file is rendered asynchronously
    by a Celery task and the export record is updated in place.
    """
    export = await finance_service.request_finance_report(
        db, data=payload, requested_by_admin_id=admin.admin_id
    )
    await record_audit_event(
        db,
        actor=admin,
        action="finance.report.request",
        resource_type="finance_report_export",
        resource_id=str(export.id),
        request_ip=request.client.host if request.client else None,
        metadata={"format": payload.format},
    )
    await db.commit()

    generate_finance_report_task.delay(str(export.id))
    return FinanceReportResponse.model_validate(export)


@router.get("/reports/{report_id}", response_model=FinanceReportResponse)
async def get_finance_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: AdminPrincipal = Depends(require_roles(*_FINANCE_ROLES)),
) -> FinanceReportResponse:
    """Poll the status of a requested report export."""
    export = await finance_service.get_report_export(db, report_id)
    return FinanceReportResponse.model_validate(export)
