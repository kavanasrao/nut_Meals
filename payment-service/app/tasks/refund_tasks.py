"""
Refund background tasks.
"""

from app.workers.celery_app import celery


@celery.task(
    bind=True,
    max_retries=3,
)
def process_refund(
    self,
    refund_id: str,
):

    print(
        f"Processing refund {refund_id}"
    )