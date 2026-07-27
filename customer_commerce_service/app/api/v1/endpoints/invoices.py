"""Invoice API endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_customer
from app.db.session import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreateRequest, InvoiceResponse
from app.services.invoice_service import InvoiceService
from app.tasks.invoice_tasks import generate_invoice_pdf

router = APIRouter(prefix="/invoices", tags=["Invoices"])
CurrentUser = Annotated[TokenPayload, Depends(require_customer)]


@router.post(
    "",
    response_model=InvoiceResponse,
    status_code=201,
    summary="Create invoice and enqueue PDF generation",
)
async def create_invoice(
    payload: InvoiceCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = InvoiceService(db)
    invoice = await svc.create_invoice(user.user_id, payload)

    # Enqueue Celery PDF generation task
    task = generate_invoice_pdf.delay(str(invoice.id))

    # Persist the Celery task ID for later status polling
    result = await db.execute(select(Invoice).where(Invoice.id == invoice.id))
    inv_orm = result.scalar_one()
    inv_orm.celery_task_id = task.id

    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse, summary="Get invoice details")
async def get_invoice(
    invoice_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    return await InvoiceService(db).get_invoice(invoice_id, user.user_id)
