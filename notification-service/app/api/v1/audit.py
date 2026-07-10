"""
Audit & compliance API. Read access restricted to `auditor` /
`messaging_admin` roles. Supports CSV/JSON compliance exports.
"""
import csv
import io
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rbac import require_auditor
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogRead, ComplianceReportRequest

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=list[AuditLogRead])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_auditor),
    message_id: uuid.UUID | None = None,
    channel: str | None = None,
    action: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    query = select(AuditLog)
    if message_id:
        query = query.where(AuditLog.message_id == message_id)
    if channel:
        query = query.where(AuditLog.channel == channel)
    if action:
        query = query.where(AuditLog.action == action)

    query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/compliance-report")
async def export_compliance_report(
    req: ComplianceReportRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_auditor),
):
    """Stream a compliance report (CSV or JSON) of audit activity in a date range."""
    query = select(AuditLog).where(
        AuditLog.created_at >= req.start_date,
        AuditLog.created_at <= req.end_date,
    )
    if req.channel:
        query = query.where(AuditLog.channel == req.channel)
    if req.status:
        query = query.where(AuditLog.status == req.status)

    result = await db.execute(query.order_by(AuditLog.created_at))
    logs = result.scalars().all()

    if req.export_format == "json":
        return [AuditLogRead.model_validate(log).model_dump(mode="json") for log in logs]

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "message_id", "actor", "action", "channel", "recipient", "status", "created_at"])
    for log in logs:
        writer.writerow([log.id, log.message_id, log.actor, log.action, log.channel, log.recipient, log.status, log.created_at])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compliance_report.csv"},
    )
