from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "notification_service",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,               # re-deliver if worker dies mid-task
    worker_prefetch_multiplier=4,
    task_default_queue="dispatch",
    task_routes={
        "app.workers.tasks.dispatch_message_task": {"queue": "dispatch"},
        "app.workers.tasks.retry_failed_messages_task": {"queue": "retry"},
        "app.workers.tasks.relay_outbox_task": {"queue": "dispatch"},
        "app.workers.tasks.process_dlq_task": {"queue": "dlq"},
    },
)

celery_app.conf.beat_schedule = {
    "relay-outbox-every-10s": {
        "task": "app.workers.tasks.relay_outbox_task",
        "schedule": 10.0,
    },
    "retry-due-messages-every-30s": {
        "task": "app.workers.tasks.retry_failed_messages_task",
        "schedule": 30.0,
    },
}
