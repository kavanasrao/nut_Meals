"""
Compliance dashboard API.

Exposes report definitions and executed report runs so the Admin CMS can
render PCI DSS / GDPR / SOC2 readiness dashboards. All endpoints require
`compliance:read` (or `compliance:manage` for creating/running reports),
so only finance/security/admin roles can see compliance posture.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUserDep, DbDep, require_permission
from app.models.compliance import ComplianceFramework
from app.schemas.compliance import (
    ComplianceReportDefinitionCreate,
    ComplianceReportDefinitionOut,
    ComplianceReportRunOut,
    ComplianceReportRunRequest,
)
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.post(
    "/definitions",
    response_model=ComplianceReportDefinitionOut,
    dependencies=[Depends(require_permission("compliance:manage"))],
)
async def create_definition(payload: ComplianceReportDefinitionCreate, db: DbDep):
    """Define a new compliance report (framework + check config). Requires `compliance:manage`."""
    service = ComplianceService(db)
    return await service.create_definition(payload)


@router.get(
    "/definitions",
    response_model=list[ComplianceReportDefinitionOut],
    dependencies=[Depends(require_permission("compliance:read"))],
)
async def list_definitions(db: DbDep):
    """List available compliance report definitions. Requires `compliance:read`."""
    service = ComplianceService(db)
    return await service.list_definitions()


@router.post(
    "/reports/run",
    response_model=ComplianceReportRunOut,
    dependencies=[Depends(require_permission("compliance:manage"))],
)
async def run_report(payload: ComplianceReportRunRequest, db: DbDep, user: CurrentUserDep):
    """Execute a compliance report definition now and return the scored result.

    Requires `compliance:manage`. For heavier frameworks this could be made
    async (Celery) the same way audit exports are; kept synchronous here since
    the built-in checks are cheap aggregate queries.
    """
    service = ComplianceService(db)
    try:
        return await service.run_report(payload.definition_id, requested_by=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/reports/runs",
    response_model=list[ComplianceReportRunOut],
    dependencies=[Depends(require_permission("compliance:read"))],
)
async def list_runs(db: DbDep, framework: ComplianceFramework | None = None):
    """List historical compliance report runs, optionally filtered by framework.
    Requires `compliance:read`. Powers the Admin CMS compliance dashboard."""
    service = ComplianceService(db)
    return await service.list_runs(framework)


@router.get(
    "/reports/runs/{run_id}",
    response_model=ComplianceReportRunOut,
    dependencies=[Depends(require_permission("compliance:read"))],
)
async def get_run(run_id: uuid.UUID, db: DbDep):
    """Fetch a single compliance report run with full findings. Requires `compliance:read`."""
    service = ComplianceService(db)
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Report run not found")
    return run
