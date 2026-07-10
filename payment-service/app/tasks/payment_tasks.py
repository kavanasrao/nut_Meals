"""
Payment background tasks.
"""

from app.workers.celery_app import celery


@celery.task(
    bind=True,
    max_retries=3,
)
def retry_failed_payment(
    self,
    payment_id: str,
):

    print(
        f"Retry payment {payment_id}"
    )