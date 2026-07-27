"""Invoice PDF generation task."""
import asyncio
import io
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionFactory
from app.models.invoice import Invoice, InvoiceStatus
from app.tasks.celery_app import celery_app
from app.utils.pdf_generator import build_invoice_pdf
from app.utils.storage import upload_to_oci

logger = logging.getLogger(__name__)


async def _generate_and_store(invoice_id: UUID) -> str:
    async with AsyncSessionFactory() as db:
        result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        try:
            pdf_bytes: bytes = build_invoice_pdf(invoice)
            object_name = f"invoices/{invoice.invoice_number}.pdf"
            pdf_url = await upload_to_oci(pdf_bytes, object_name)

            invoice.status = InvoiceStatus.GENERATED
            invoice.pdf_url = pdf_url
        except Exception as exc:
            invoice.status = InvoiceStatus.FAILED
            await db.commit()
            raise

        await db.commit()
        return pdf_url


@celery_app.task(
    name="app.tasks.invoice_tasks.generate_invoice_pdf",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_invoice_pdf(self, invoice_id: str) -> dict:
    """Generate GST invoice PDF and upload to OCI Object Storage."""
    try:
        url = asyncio.get_event_loop().run_until_complete(
            _generate_and_store(UUID(invoice_id))
        )
        logger.info("Invoice PDF generated: %s -> %s", invoice_id, url)
        return {"invoice_id": invoice_id, "pdf_url": url}
    except Exception as exc:
        logger.exception("Invoice PDF generation failed for %s", invoice_id)
        raise self.retry(exc=exc)
