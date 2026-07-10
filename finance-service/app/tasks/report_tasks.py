"""Celery tasks for scheduled financial report generation and compliance export."""

import asyncio
import json
import logging
from datetime import date

from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.database import db_session_ctx
from app.services.trial_balance_service import TrialBalanceService

logger: logging.Logger = get_task_logger(__name__)


@shared_task(name="app.tasks.report_tasks.snapshot_trial_balance")
def snapshot_trial_balance() -> dict:
    """
    Nightly job that generates the trial balance as of "today" and writes
    it to durable storage (object storage bucket in production; this
    scaffold logs a summary) for tax/audit compliance record-keeping.
    Retained snapshots let auditors see the ledger's state on any given
    day without re-deriving it from the full journal history.
    """
    return asyncio.run(_snapshot_async())


async def _snapshot_async() -> dict:
    today = date.today().isoformat()
    async with db_session_ctx() as db:
        service = TrialBalanceService(db)
        report = await service.generate(as_of_date=today)

    summary = {
        "as_of_date": today,
        "total_debit_minor": report.total_debit_minor,
        "total_credit_minor": report.total_credit_minor,
        "is_balanced": report.is_balanced,
        "row_count": len(report.rows),
    }
    logger.info("Trial balance snapshot for %s: %s", today, json.dumps(summary))
    # In production: upload report.model_dump_json() to OCI Object Storage
    # under a path like reports/trial-balance/{today}.json, and record the
    # object key in an audit log entry (AuditAction.REPORT_EXPORTED).
    return summary
