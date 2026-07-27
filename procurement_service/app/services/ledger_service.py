import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import LedgerEntrySource, LedgerEntryType
from app.schemas.vendor import VendorLedgerEntryCreate
from app.services.finance_client import FinanceServiceClient, FinanceServiceError
from app.services.vendor_service import VendorService

logger = logging.getLogger(__name__)


class LedgerService:
    """
    Orchestrates writing a VendorLedgerEntry and (best-effort, synchronously)
    syncing it to the Finance Service. If the sync fails, the local entry is
    still committed and `finance_service_synced` stays False — a background
    Celery task (see tasks/invoice_tasks.py) retries the sync later.
    """

    def __init__(self, db: AsyncSession, finance_client: FinanceServiceClient | None = None):
        self.db = db
        self.vendor_service = VendorService(db)
        self.finance_client = finance_client or FinanceServiceClient()

    async def record_invoice_booked(
        self, vendor_id: uuid.UUID, invoice_id: uuid.UUID, amount, description: str
    ):
        entry = await self.vendor_service.add_ledger_entry(
            vendor_id,
            VendorLedgerEntryCreate(
                entry_type=LedgerEntryType.CREDIT,
                source=LedgerEntrySource.INVOICE,
                reference_id=invoice_id,
                amount=amount,
                description=description,
            ),
        )
        await self._sync_to_finance(entry)
        return entry

    async def record_payment(
        self, vendor_id: uuid.UUID, payment_reference: uuid.UUID, amount, description: str
    ):
        entry = await self.vendor_service.add_ledger_entry(
            vendor_id,
            VendorLedgerEntryCreate(
                entry_type=LedgerEntryType.DEBIT,
                source=LedgerEntrySource.PAYMENT,
                reference_id=payment_reference,
                amount=amount,
                description=description,
            ),
        )
        await self._sync_to_finance(entry)
        return entry

    async def _sync_to_finance(self, entry) -> None:
        try:
            ref = await self.finance_client.post_journal_entry(
                vendor_id=str(entry.vendor_id),
                entry_type=entry.entry_type.value,
                amount=entry.amount,
                source=entry.source.value,
                reference_id=str(entry.reference_id) if entry.reference_id else None,
                description=entry.description,
            )
            entry.finance_service_synced = True
            entry.finance_service_ref = ref
            await self.db.commit()
        except FinanceServiceError:
            logger.warning(
                "Ledger entry %s created locally but not yet synced to Finance Service; "
                "will be retried by background task.",
                entry.id,
            )
