"""Celery application for background tracking sync + cache refresh jobs."""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "logistics_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.tracking_sync", "app.tasks.cache_refresh"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "sync-active-shipment-tracking": {
        "task": "app.tasks.tracking_sync.sync_all_active_shipments",
        "schedule": crontab(minute="*/15"),
    },
    "refresh-serviceability-cache": {
        "task": "app.tasks.cache_refresh.refresh_serviceability_cache",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}
