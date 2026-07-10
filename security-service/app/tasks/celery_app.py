"""
Celery application for the Security Service.

Handles two categories of background work:
  1. Consuming audit events published by other services (high-volume,
     append-only writes) -- see tasks.audit_tasks.ingest_audit_event.
  2. Slower/expensive jobs kicked off from the API layer, like audit log
     exports and (optionally) compliance report runs for heavier frameworks.

Broker/result backend are Redis, matching the rest of the nut_meals stack.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "security_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.audit_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=4,
    task_default_queue="security_service",
    task_routes={
        "app.tasks.audit_tasks.ingest_audit_event": {"queue": "audit_events"},
        "app.tasks.audit_tasks.run_audit_export": {"queue": "audit_exports"},
        "app.tasks.audit_tasks.flush_audit_batch": {"queue": "audit_events"},
    },
    beat_schedule={
        "flush-audit-batch-every-10s": {
            "task": "app.tasks.audit_tasks.flush_audit_batch",
            "schedule": 10.0,
        },
        "purge-old-waf-rate-limit-keys-nightly": {
            "task": "app.tasks.audit_tasks.cleanup_stale_export_jobs",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
