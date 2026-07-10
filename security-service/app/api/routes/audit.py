"""
Audit log API.

- `POST /audit/logs` — low-volume direct write path (admin tools, backfills).
  High-volume writes from other services go through the Celery/Redis pipeline
  in app/tasks/audit_tasks.py instead, to avoid a synchronous HTTP round-trip
  on every order/payment/inventory action.
- `GET /audit/logs` — filtered, paginated read access for auditors.
- `POST /audit/logs/export` — kicks off an async export job (CSV/JSON).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DbDep, require_permission
from app.schemas.audit import (
    AuditExportJobOut,
    AuditExportRequest,
    AuditLogCreate,
    AuditLogFilter,
    AuditLogOut,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post(
    "/logs",
    response_model=AuditLogOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("audit:write"))],
)
async def create_audit_log(payload: AuditLogCreate, db: DbDep):
    """Record a single audit event synchronously. Requires `audit:write`."""
    service = AuditService(db)
    return await service.create_log(payload)


@router.get(
    "/logs",
    response_model=list[AuditLogOut],
    dependencies=[Depends(require_permission("audit:read"))],
)
async def list_audit_logs(db: DbDep, filters: AuditLogFilter = Depends()):
    """List audit logs with filters (user, action, service, date range). Requires `audit:read`."""
    service = AuditService(db)
    return await service.list_logs(filters)


@router.post(
    "/logs/export",
    response_model=AuditExportJobOut,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("audit:export"))],
)
async def export_audit_logs(payload: AuditExportRequest, db: DbDep, user: CurrentUserDep):
    """Kick off an async export of audit logs for compliance/legal requests. Requires `audit:export`.

    Returns immediately with a job id; the Celery worker performs the actual
    export (see app.tasks.audit_tasks.run_audit_export). Poll
    GET /audit/logs/export/{job_id} for status.
    """
    from app.tasks.audit_tasks import run_audit_export

    service = AuditService(db)
    job = await service.create_export_job(requested_by=user.user_id, filters=payload.filters)
    run_audit_export.delay(str(job.id))
    return job


@router.get(
    "/logs/export/{job_id}",
    response_model=AuditExportJobOut,
    dependencies=[Depends(require_permission("audit:export"))],
)
async def get_export_job(job_id: uuid.UUID, db: DbDep):
    """Poll the status of an audit export job. Requires `audit:export`."""
    service = AuditService(db)
    job = await service.get_export_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export job not found")
    return job
