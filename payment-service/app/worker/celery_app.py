"""
Celery configuration.
"""

from celery import Celery

from app.core.config import settings

celery = Celery(
    "payment-service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(

    task_serializer="json",

    result_serializer="json",

    accept_content=["json"],

    timezone="Asia/Kolkata",

    enable_utc=True,

    task_track_started=True,

    task_ignore_result=False,

    worker_prefetch_multiplier=1,
)

celery.autodiscover_tasks(
    [
        "app.tasks",
    ]
)