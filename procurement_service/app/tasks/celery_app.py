from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "procurement_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.invoice_tasks",
        "app.tasks.po_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    task_default_retry_delay=60,
)

celery_app.conf.beat_schedule = {
    "reconcile-pending-invoices": {
        "task": "app.tasks.invoice_tasks.reconcile_pending_invoices",
        "schedule": settings.INVOICE_RECONCILIATION_INTERVAL_MINUTES * 60,
    },
    "retry-unsynced-ledger-entries": {
        "task": "app.tasks.invoice_tasks.retry_unsynced_ledger_entries",
        "schedule": 15 * 60,  # every 15 minutes
    },
    "send-po-approval-reminders": {
        "task": "app.tasks.po_tasks.send_po_approval_reminders",
        "schedule": crontab(hour=9, minute=0),  # daily at 09:00 UTC
    },
    "send-po-delivery-reminders": {
        "task": "app.tasks.po_tasks.send_po_delivery_reminders",
        "schedule": crontab(hour=9, minute=30),  # daily at 09:30 UTC
    },
}
