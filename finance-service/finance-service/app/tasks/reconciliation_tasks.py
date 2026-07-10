"""
Celery tasks driving the asynchronous reconciliation workflow.

Celery tasks are synchronous by nature; since the rest of the app is async
(SQLAlchemy async engine, httpx async client), each task uses `asyncio.run`
to drive a short-lived async workflow per invocation. This keeps a single
async codebase (app.services.*) reusable from both FastAPI request handlers
and Celery workers, rather than maintaining parallel sync/async service
implementations.
"""

import asyncio
import logging
import uuid

from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.database import db_session_ctx
from app.services.reconciliation_service import ReconciliationService

logger: logging.Logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.reconciliation_tasks.run_reconciliation_matching",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def run_reconciliation_matching(self, run_id: str, actor: str) -> dict:
    """
    Runs the matching pass for a previously-created ReconciliationRun.
    Triggered synchronously after `POST /reconciliation/runs`, and also
    usable for manual re-runs (e.g. after upstream Orders service recovers
    from an outage that caused UNMATCHED exceptions).
    """
    try:
        return asyncio.run(_run_matching_async(run_id, actor))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Reconciliation matching failed for run_id=%s", run_id)
        raise self.retry(exc=exc) from exc


async def _run_matching_async(run_id: str, actor: str) -> dict:
    async with db_session_ctx() as db:
        service = ReconciliationService(db)
        run = await service.run_matching(uuid.UUID(run_id), actor=actor)
        return {
            "run_id": str(run.id),
            "status": run.status.value,
            "matched": run.matched_records,
            "exceptions": run.exception_records,
        }


@shared_task(name="app.tasks.reconciliation_tasks.poll_gateway_settlements")
def poll_gateway_settlements(provider: str) -> dict:
    """
    Scheduled task (celery beat) that pulls new settlement files from a
    payment gateway / bank (e.g. Juspay settlement API, Kotak SFTP drop)
    and creates a ReconciliationRun for them, then triggers matching.

    The actual file-fetch/parse logic is provider-specific and lives in
    app.integrations.<provider>_settlement_fetcher (not shown here - this
    task is the orchestration entrypoint). In this scaffold it logs a
    no-op so the schedule is wired up and testable without real credentials.
    """
    logger.info(
        "Polling settlements for provider=%s (integration adapter not configured in this environment)", provider
    )
    return {"provider": provider, "new_records": 0, "status": "no_new_settlements"}
