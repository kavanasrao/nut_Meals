"""Invoice creation and GST computation."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreateRequest, InvoiceResponse


def _generate_invoice_number() -> str:
    now = datetime.now(timezone.utc)
    fy_year = now.year if now.month >= settings.INVOICE_FY_START_MONTH else now.year - 1
    fy_str = f"{fy_year}-{str(fy_year + 1)[-2:]}"
    unique = str(uuid.uuid4())[:8].upper()
    return f"{settings.INVOICE_PREFIX}/{fy_str}/{unique}"


class InvoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_invoice(
        self, user_id: UUID, payload: InvoiceCreateRequest
    ) -> InvoiceResponse:
        taxable = payload.subtotal - payload.discount_amount
        cgst = (taxable * payload.cgst_rate / 100).quantize(Decimal("0.01"))
        sgst = (taxable * payload.sgst_rate / 100).quantize(Decimal("0.01"))
        igst = (taxable * payload.igst_rate / 100).quantize(Decimal("0.01"))
        total = taxable + cgst + sgst + igst

        invoice = Invoice(
            invoice_number=_generate_invoice_number(),
            order_id=payload.order_id,
            user_id=user_id,
            billing_name=payload.billing_name,
            billing_address=payload.billing_address,
            billing_gstin=payload.billing_gstin,
            subtotal=payload.subtotal,
            cgst_rate=payload.cgst_rate,
            sgst_rate=payload.sgst_rate,
            igst_rate=payload.igst_rate,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            discount_amount=payload.discount_amount,
            total_amount=total,
            line_items=[i.model_dump(mode="json") for i in payload.line_items],
            status=InvoiceStatus.PENDING,
        )
        self.db.add(invoice)
        await self.db.flush()
        return InvoiceResponse.model_validate(invoice)

    async def get_invoice(self, invoice_id: UUID, user_id: UUID) -> InvoiceResponse:
        result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id, Invoice.user_id == user_id)
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
        return InvoiceResponse.model_validate(invoice)

    async def mark_generated(self, invoice_id: UUID, pdf_url: str) -> None:
        result = await self.db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if invoice:
            invoice.status = InvoiceStatus.GENERATED
            invoice.pdf_url = pdf_url
            await self.db.flush()
