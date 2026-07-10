"""Routes for exportable compliance/audit reports."""
import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.security import Principal, enforce_https, require_roles
from app.models.audit import AuditLog

router = APIRouter(prefix="/v1/reports", tags=["reports"], dependencies=[Depends(enforce_https)])


@router.get("/audit-log.csv")
async def export_audit_log_csv(
    start: datetime = Query(...),
    end: datetime = Query(...),
    entity_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_roles("logistics_admin", "compliance_officer")),
):
    """
    Export audit log entries within a date range as CSV, for compliance
    reporting. Restricted to admin / compliance roles.
    """
    stmt = select(AuditLog).where(AuditLog.created_at >= start, AuditLog.created_at <= end)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    stmt = stmt.order_by(AuditLog.created_at)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "entity_type", "entity_id", "action", "actor", "details", "created_at"])
    for row in rows:
        writer.writerow(
            [row.id, row.entity_type, row.entity_id, row.action, row.actor, row.details, row.created_at.isoformat()]
        )
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=logistics_audit_log.csv"},
    )
