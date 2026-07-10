"""
Celery application configuration for the SEO service.

Handles background work that must not block request/response cycles:
sitemap regeneration, structured-data resync, and bulk AI export
generation. Redis is used as both broker and result backend, matching
the rest of the nut_Meals platform.
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "seo_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.sitemap_tasks", "app.tasks.schema_sync_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=15 * 60,
    task_soft_time_limit=10 * 60,
    task_default_retry_delay=30,
)

# Periodic schedule: full incremental resync every 15 minutes, full
# sitemap index rebuild nightly, AI export refresh daily.
celery_app.conf.beat_schedule = {
    "sitemap-incremental-resync": {
        "task": "app.tasks.sitemap_tasks.rebuild_sitemap_task",
        "schedule": crontab(minute="*/15"),
        "args": (None, False),
    },
    "sitemap-nightly-full-rebuild": {
        "task": "app.tasks.sitemap_tasks.rebuild_sitemap_task",
        "schedule": crontab(hour=3, minute=0),
        "args": (None, True),
    },
    "ai-export-daily": {
        "task": "app.tasks.sitemap_tasks.generate_ai_export_task",
        "schedule": crontab(hour=4, minute=0),
        "args": (None,),
    },
}
