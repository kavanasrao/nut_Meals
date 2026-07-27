import logging
import uuid

from celery import shared_task
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.base import InvoiceStatus
from app.models.invoice import PurchaseInvoice
from app.models.vendor import VendorLedgerEntry
from app.services.finance_client import FinanceServiceClient, FinanceServiceError
from app.services.invoice_service import InvoiceService
from app.tasks.utils import run_async

logger = logging.getLogger(__name__)


@shared_task(name="app.tasks.invoice_tasks.reconcile_invoice", bind=True, max_retries=3)
def reconcile_invoice(self, invoice_id: str):
    """Run the 3-way match for a single invoice (triggered after GRN confirmation)."""
    try:
        run_async(lambda: _reconcile_invoice(invoice_id))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to reconcile invoice %s", invoice_id)
        raise self.retry(exc=exc, countdown=30) from exc


async def _reconcile_invoice(invoice_id: str) -> None:
    async with AsyncSessionLocal() as db:
        service = InvoiceService(db)
        await service.match_against_grn(uuid.UUID(invoice_id))


@shared_task(name="app.tasks.invoice_tasks.reconcile_pending_invoices")
def reconcile_pending_invoices():
    """Periodic sweep: 3-way match every invoice still in RECEIVED status."""
    return run_async(_reconcile_pending_invoices)


async def _reconcile_pending_invoices() -> dict:
    processed = 0
    async with AsyncSessionLocal() as db:
        stmt = select(PurchaseInvoice.id).where(
            PurchaseInvoice.status == InvoiceStatus.RECEIVED
        )
        result = await db.execute(stmt)
        invoice_ids = [row[0] for row in result.all()]

        service = InvoiceService(db)
        for invoice_id in invoice_ids:
            try:
                await service.match_against_grn(invoice_id)
                processed += 1
            except Exception:  # noqa: BLE001
                logger.exception("Reconciliation failed for invoice %s", invoice_id)

    logger.info("Reconciled %d pending invoices", processed)
    return {"processed": processed}


@shared_task(name="app.tasks.invoice_tasks.retry_unsynced_ledger_entries")
def retry_unsynced_ledger_entries():
    """Retries pushing ledger entries to the Finance Service that failed earlier."""
    return run_async(_retry_unsynced_ledger_entries)


async def _retry_unsynced_ledger_entries() -> dict:
    synced = 0
    async with AsyncSessionLocal() as db:
        stmt = select(VendorLedgerEntry).where(
            VendorLedgerEntry.finance_service_synced.is_(False)
        )
        result = await db.execute(stmt)
        entries = list(result.scalars().all())

        client = FinanceServiceClient()
        for entry in entries:
            try:
                ref = await client.post_journal_entry(
                    vendor_id=str(entry.vendor_id),
                    entry_type=entry.entry_type.value,
                    amount=entry.amount,
                    source=entry.source.value,
                    reference_id=str(entry.reference_id) if entry.reference_id else None,
                    description=entry.description,
                )
                entry.finance_service_synced = True
                entry.finance_service_ref = ref
                synced += 1
            except FinanceServiceError:
                logger.warning("Retry failed for ledger entry %s", entry.id)
                continue
        await db.commit()

    logger.info("Synced %d previously-unsynced ledger entries to Finance Service", synced)
    return {"synced": synced}
