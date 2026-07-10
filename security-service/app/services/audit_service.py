"""
Audit log service: durable writes, filtered queries, and export orchestration.

Writes here are intentionally simple/fast (single INSERT) since the
high-volume path is the Celery consumer in app/tasks/audit_tasks.py, which
batches events coming off Redis from all other services. This module is
shared by both that consumer and the direct HTTP POST route.
"""
import csv
import io
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditExportJob, AuditLog
from app.schemas.audit import AuditLogCreate, AuditLogFilter


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(self, payload: AuditLogCreate) -> AuditLog:
        """Persist a single audit event. Audit logs are append-only: no update/delete method exists."""
        log = AuditLog(**payload.model_dump())
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def bulk_create(self, payloads: list[AuditLogCreate]) -> int:
        """Batch insert, used by the Celery consumer for throughput."""
        logs = [AuditLog(**p.model_dump()) for p in payloads]
        self.db.add_all(logs)
        await self.db.commit()
        return len(logs)

    def _apply_filters(self, stmt, filters: AuditLogFilter):
        if filters.user_id:
            stmt = stmt.where(AuditLog.user_id == filters.user_id)
        if filters.action:
            stmt = stmt.where(AuditLog.action == filters.action)
        if filters.service:
            stmt = stmt.where(AuditLog.service == filters.service)
        if filters.resource_id:
            stmt = stmt.where(AuditLog.resource_id == filters.resource_id)
        if filters.severity:
            stmt = stmt.where(AuditLog.severity == filters.severity)
        if filters.start_date:
            stmt = stmt.where(AuditLog.created_at >= filters.start_date)
        if filters.end_date:
            stmt = stmt.where(AuditLog.created_at <= filters.end_date)
        return stmt

    async def list_logs(self, filters: AuditLogFilter) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        stmt = self._apply_filters(stmt, filters)
        stmt = stmt.limit(filters.limit).offset(filters.offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_export_job(self, requested_by: str, filters: AuditLogFilter) -> AuditExportJob:
        job = AuditExportJob(
            requested_by=requested_by,
            status="pending",
            filters_json=filters.model_dump(mode="json"),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_export_job(self, job_id: uuid.UUID) -> Optional[AuditExportJob]:
        return await self.db.get(AuditExportJob, job_id)

    async def run_export(self, job_id: uuid.UUID) -> None:
        """Executed by the Celery worker: pulls matching rows and writes CSV/JSON.

        In production `result_path` would be an OCI Object Storage URI; here
        we compute the serialized payload and store its path for download via
        a signed-URL endpoint (not shown) served by the export bucket.
        """
        job = await self.db.get(AuditExportJob, job_id)
        if job is None:
            return

        job.status = "running"
        await self.db.commit()

        try:
            filters = AuditLogFilter(**(job.filters_json or {}))
            filters.limit = 10_000  # exports bypass the normal page-size cap
            logs = await self.list_logs(filters)

            export_format = "csv"
            if export_format == "csv":
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(
                    ["id", "user_id", "action", "service", "resource_id", "severity", "created_at"]
                )
                for log in logs:
                    writer.writerow(
                        [str(log.id), log.user_id, log.action, log.service, log.resource_id, log.severity.value, log.created_at.isoformat()]
                    )
                content = buffer.getvalue()
            else:
                content = json.dumps([
                    {
                        "id": str(log.id),
                        "user_id": log.user_id,
                        "action": log.action,
                        "service": log.service,
                        "resource_id": log.resource_id,
                        "severity": log.severity.value,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs
                ])

            # Placeholder for the real OCI Object Storage upload call.
            result_path = f"oci://nutmeals-compliance-exports/audit/{job.id}.csv"
            _ = content  # would be uploaded to `result_path` here

            job.status = "completed"
            job.result_path = result_path
            job.completed_at = datetime.utcnow()
        except Exception as exc:  # noqa: BLE001 - export job must record any failure
            job.status = "failed"
            job.error_message = str(exc)
        finally:
            await self.db.commit()
