"""
Celery application for the Finance service's background jobs.

Two categories of jobs:
  1. Reconciliation matching (triggered on-demand after a settlement batch
     is imported via the API, or on a schedule via celery beat for
     provider SFTP pulls).
  2. Scheduled report generation / export (e.g. nightly trial balance
     snapshot for tax compliance archival).

Broker and result backend are Redis, matching the rest of the platform's
microservices (each service uses its own Redis DB index to avoid key
collisions - see REDIS_URL / CELERY_BROKER_URL / CELERY_RESULT_BACKEND
in app.core.config).
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "finance_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.reconciliation_tasks", "app.tasks.report_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_time_limit=15 * 60,
    task_soft_time_limit=10 * 60,
)

# Celery beat schedule: periodic settlement pulls + nightly report snapshot.
celery_app.conf.beat_schedule = {
    "poll-juspay-settlements-hourly": {
        "task": "app.tasks.reconciliation_tasks.poll_gateway_settlements",
        "schedule": crontab(minute=0),  # every hour
        "args": ("juspay",),
    },
    "poll-kotak-settlements-daily": {
        "task": "app.tasks.reconciliation_tasks.poll_gateway_settlements",
        "schedule": crontab(hour=2, minute=30),  # 02:30 IST daily
        "args": ("kotak_bank",),
    },
    "nightly-trial-balance-snapshot": {
        "task": "app.tasks.report_tasks.snapshot_trial_balance",
        "schedule": crontab(hour=23, minute=45),
    },
}
