"""Celery application for the User Service.

Handles background delivery work that must not block the request/response
cycle:
  - OTP delivery (SMS/Email) for OTP login
  - Password reset email delivery
  - Login alert notifications

Broker/result backend are Redis, matching the rest of the nut_meals stack.
Run the worker with:

    celery -A app.tasks.celery_app worker --loglevel=info -Q user_service

"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "user_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=4,
    task_default_queue="user_service",
    task_routes={
        "app.tasks.notification_tasks.send_otp_task": {"queue": "user_service"},
        "app.tasks.notification_tasks.send_password_reset_email_task": {"queue": "user_service"},
        "app.tasks.notification_tasks.send_login_alert_task": {"queue": "user_service"},
    },
)
