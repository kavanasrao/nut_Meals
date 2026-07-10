"""
Celery application instance for the Admin CMS Service. Uses Redis as
both broker and result backend. Beat schedule drives periodic jobs:
nightly analytics aggregation, finance cache refresh, and scheduled-post
publishing (checked every minute).
"""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "admin_cms_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.analytics_tasks",
        "app.tasks.content_tasks",
        "app.tasks.finance_tasks",
    ],
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
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "aggregate-daily-kpis": {
        "task": "app.tasks.analytics_tasks.aggregate_daily_kpis_task",
        "schedule": crontab(hour=1, minute=0),  # 01:00 UTC daily, after upstream day-close
    },
    "refresh-finance-summary-cache": {
        "task": "app.tasks.finance_tasks.refresh_current_month_summary_task",
        "schedule": crontab(hour="*/1", minute=15),  # hourly
    },
    "publish-scheduled-content": {
        "task": "app.tasks.content_tasks.publish_due_scheduled_content_task",
        "schedule": crontab(minute="*"),  # every minute
    },
}
