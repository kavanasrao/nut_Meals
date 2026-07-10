"""
Settlement background jobs.
"""

from app.worker.celery_app import celery


@celery.task
def reconcile_settlements():

    print(
        "Settlement reconciliation started."
    )
