"""
Celery application for the Inventory Service.

Two kinds of background work:
1. Scheduled (Celery beat) — periodic sweep releasing expired reservations,
   as a safety net in case a per-reservation countdown task is lost (worker
   restart, broker eviction, etc).
2. On-demand tasks — dispatched from API routes, e.g. per-reservation
   auto-release timers and post-completion batch finalization retries.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "inventory_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.reservation_tasks", "app.tasks.batch_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=30,
    task_time_limit=300,
)

celery_app.conf.beat_schedule = {
    "sweep-expired-reservations": {
        "task": "app.tasks.reservation_tasks.sweep_expired_reservations_task",
        "schedule": crontab(minute="*/2"),  # safety-net sweep every 2 minutes
    },
}
