import logging
from datetime import date, timedelta

from celery import shared_task
from sqlalchemy import select

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.base import PurchaseOrderStatus
from app.models.purchase_order import PurchaseOrder
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)
settings = get_settings()


@shared_task(name="app.tasks.po_tasks.send_po_approval_reminders")
def send_po_approval_reminders():
    """Reminds approvers about POs stuck in pending_approval."""
    return run_async(_send_po_approval_reminders)


async def _send_po_approval_reminders() -> dict:
    async with AsyncSessionLocal() as db:
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.status == PurchaseOrderStatus.PENDING_APPROVAL
        )
        result = await db.execute(stmt)
        pending = list(result.scalars().all())

    for po in pending:
        _notify(
            event="po_pending_approval",
            po_number=po.po_number,
            message=f"PO {po.po_number} has been awaiting approval since {po.created_at}",
        )

    logger.info("Sent %d PO approval reminders", len(pending))
    return {"reminders_sent": len(pending)}


@shared_task(name="app.tasks.po_tasks.send_po_delivery_reminders")
def send_po_delivery_reminders():
    """Reminds procurement officers about POs whose expected delivery is imminent."""
    return run_async(_send_po_delivery_reminders)


async def _send_po_delivery_reminders() -> dict:
    threshold = date.today() + timedelta(days=settings.PO_REMINDER_DAYS_BEFORE_DUE)
    async with AsyncSessionLocal() as db:
        stmt = select(PurchaseOrder).where(
            PurchaseOrder.status.in_(
                [PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PARTIALLY_RECEIVED]
            ),
            PurchaseOrder.expected_delivery_date.isnot(None),
            PurchaseOrder.expected_delivery_date <= threshold,
        )
        result = await db.execute(stmt)
        due_soon = list(result.scalars().all())

    for po in due_soon:
        _notify(
            event="po_delivery_due_soon",
            po_number=po.po_number,
            message=f"PO {po.po_number} is expected to be delivered on {po.expected_delivery_date}",
        )

    logger.info("Sent %d PO delivery reminders", len(due_soon))
    return {"reminders_sent": len(due_soon)}


def _notify(event: str, po_number: str, message: str) -> None:
    """
    Placeholder notification sink. In production this publishes to the
    Notification Service (e.g. via Redis pub/sub or an HTTP call) rather
    than sending emails directly from this worker.
    """
    logger.info("[notify:%s] %s | %s", event, po_number, message)
