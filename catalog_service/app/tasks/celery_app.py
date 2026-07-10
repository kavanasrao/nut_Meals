"""Celery application instance for the Catalog Service.

Broker/backend: Redis. Used for:
  - review moderation side-effects (aggregate recompute, notifications)
  - redirect analytics sync + stale redirect cleanup
"""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "catalog_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.moderation_tasks", "app.tasks.redirect_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_max_tasks_per_child=200,
    timezone="UTC",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "sync-redirect-analytics-hourly": {
        "task": "app.tasks.redirect_tasks.flush_redirect_analytics",
        "schedule": crontab(minute=0),
    },
    "cleanup-stale-redirect-logs-daily": {
        "task": "app.tasks.redirect_tasks.cleanup_old_redirect_logs",
        "schedule": crontab(hour=3, minute=0),
    },
}
