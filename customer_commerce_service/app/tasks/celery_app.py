"""Celery application factory with beat schedule."""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "customer_commerce",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.cart_tasks",
        "app.tasks.invoice_tasks",
    ],
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
    # Beat schedule — runs inside celery beat process
    beat_schedule={
        "abandoned-cart-recovery": {
            "task": "app.tasks.cart_tasks.send_abandoned_cart_emails",
            "schedule": crontab(
                minute=settings.CART_RECOVERY_CRON_MINUTE,
                hour=settings.CART_RECOVERY_CRON_HOUR,
            ),
        },
    },
)
