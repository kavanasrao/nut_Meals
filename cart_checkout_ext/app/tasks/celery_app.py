"""Celery application instance + periodic task (beat) schedule for the
Cart/Checkout Extensions service."""
from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cart_checkout_ext",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.subscription_tasks", "app.tasks.gift_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
)

celery_app.conf.beat_schedule = {
    "process-due-subscription-renewals": {
        "task": "app.tasks.subscription_tasks.process_due_renewals",
        "schedule": crontab(minute="0", hour="*"),  # hourly sweep
    },
    "send-renewal-notices": {
        "task": "app.tasks.subscription_tasks.send_upcoming_renewal_notices",
        "schedule": crontab(minute="30", hour="*"),  # hourly, offset from renewals
    },
}
