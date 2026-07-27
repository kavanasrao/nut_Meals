"""
GST Service.

Responsible for:

- GST Rate management
- GST calculation
- GST Invoice creation/posting
- Journal integration
- Audit logging
- Period lock validation
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.core.audit import AuditAction, write_audit_log
from app.services.journal_service import JournalService
from sqlalchemy import select

from app.models.gst import (
    GSTRate,
    GSTInvoice,
    GSTInvoiceLine,
    GSTInvoiceStatus,
)
from app.schemas.gst import (
    GSTRateCreate,
    GSTRateUpdate,
    GSTInvoiceCreate,
)
from app.models.journal import JournalEntry
from app.models.audit_lock import PeriodLock, PeriodLockStatus


class GSTService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # GST RATE CRUD
    # ==========================================================

    async def create_rate(
        self,
        data: GSTRateCreate,
    ) -> GSTRate:

        existing = await self.db.scalar(
            select(GSTRate).where(
                GSTRate.category_code == data.category_code,
                GSTRate.is_active.is_(True),
            )
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="GST rate already exists for this category.",
            )

        rate = GSTRate(**data.model_dump())

        self.db.add(rate)

        await self.db.commit()
        await self.db.refresh(rate)

        return rate

    async def get_rate(
        self,
        rate_id: UUID,
    ) -> GSTRate:

        rate = await self.db.get(GSTRate, rate_id)

        if not rate:
            raise HTTPException(
                status_code=404,
                detail="GST rate not found.",
            )

        return rate

    async def list_rates(self):

        result = await self.db.execute(
            select(GSTRate).order_by(GSTRate.category_code)
        )

        return result.scalars().all()

    async def update_rate(
        self,
        rate_id: UUID,
        data: GSTRateUpdate,
    ) -> GSTRate:

        rate = await self.get_rate(rate_id)

        for key, value in data.model_dump(
            exclude_unset=True
        ).items():
            setattr(rate, key, value)

        await self.db.commit()
        await self.db.refresh(rate)

        return rate

    async def delete_rate(
        self,
        rate_id: UUID,
    ):

        rate = await self.get_rate(rate_id)

        rate.is_active = False

        await self.db.commit()

        return {"message": "GST rate deactivated."}

    # ==========================================================
    # HELPERS
    # ==========================================================

    @staticmethod
    def determine_tax_type(
        seller_state: str,
        customer_state: str,
    ) -> str:

        if seller_state == customer_state:
            return "INTRA"

        return "INTER"

    async def calculate_gst(
        self,
        category_code: str,
        taxable_amount_minor: int,
        seller_state: str,
        customer_state: str,
    ) -> dict:

        rate = await self.db.scalar(
            select(GSTRate).where(
                GSTRate.category_code == category_code,
                GSTRate.is_active.is_(True),
            )
        )

        if not rate:
            raise HTTPException(
                status_code=404,
                detail=f"No GST rate configured for {category_code}",
            )

        gst = (
            taxable_amount_minor
            * rate.rate_basis_points
            // 10000
        )

        tax_type = self.determine_tax_type(
            seller_state,
            customer_state,
        )

        if tax_type == "INTRA":

            cgst = gst // 2
            sgst = gst - cgst

            return {
                "cgst": cgst,
                "sgst": sgst,
                "igst": 0,
            }

        return {
            "cgst": 0,
            "sgst": 0,
            "igst": gst,
        }



    # ==========================================================
    # GST INVOICE
    # ==========================================================

async def create_invoice(
        self,
        data: GSTInvoiceCreate,
    ) -> GSTInvoice:
        """
        Creates a GST invoice and calculates GST for every line.
        """

        try:

            invoice = GSTInvoice(
                invoice_number=data.invoice_number,
                order_reference=data.order_reference,
                invoice_date=data.invoice_date,
                seller_state_code=data.seller_state_code,
                customer_state_code=data.customer_state_code,
                created_by=data.created_by,
                currency="INR",
                status=GSTInvoiceStatus.DRAFT,
            )

            self.db.add(invoice)
            await self.db.flush()

            taxable_total = 0
            cgst_total = 0
            sgst_total = 0
            igst_total = 0

            line_number = 1

            for item in data.lines:

                gst = await self.calculate_gst(
                    category_code=item.category_code,
                    taxable_amount_minor=item.taxable_amount_minor,
                    seller_state=data.seller_state_code,
                    customer_state=data.customer_state_code,
                )

                line = GSTInvoiceLine(
                    invoice_id=invoice.id,
                    line_number=line_number,
                    product_reference=item.product_reference,
                    category_code=item.category_code,
                    taxable_amount_minor=item.taxable_amount_minor,
                    cgst_amount_minor=gst["cgst"],
                    sgst_amount_minor=gst["sgst"],
                    igst_amount_minor=gst["igst"],
                    description=item.description,
                )

                self.db.add(line)

                taxable_total += item.taxable_amount_minor
                cgst_total += gst["cgst"]
                sgst_total += gst["sgst"]
                igst_total += gst["igst"]

                line_number += 1

            invoice.taxable_amount_minor = taxable_total
            invoice.cgst_amount_minor = cgst_total
            invoice.sgst_amount_minor = sgst_total
            invoice.igst_amount_minor = igst_total

            invoice.total_gst_amount_minor = (
                cgst_total
                + sgst_total
                + igst_total
            )

            invoice.total_invoice_amount_minor = (
                taxable_total
                + invoice.total_gst_amount_minor
            )

            invoice.is_interstate = (
                data.seller_state_code
                != data.customer_state_code
            )

            await self.db.commit()
            await self.db.refresh(invoice)

            return invoice

        except SQLAlchemyError:

            await self.db.rollback()

            raise HTTPException(
                status_code=500,
                detail="Unable to create GST invoice.",
            )  
        


    # ==========================================================
    # PERIOD LOCK
    # ==========================================================

async def _ensure_period_open(
        self,
        invoice_date: date,
    ) -> None:

        period = invoice_date.strftime("%Y-%m")

        lock = await self.db.scalar(
            select(PeriodLock).where(
                PeriodLock.period == period
            )
        )

        if (
            lock
            and lock.status == PeriodLockStatus.LOCKED
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Accounting period {period} is locked.",
            )

    # ==========================================================
    # POST GST INVOICE
    # ==========================================================

async def post_invoice(
        self,
        invoice_id: UUID,
        posted_by: str,
    ) -> GSTInvoice:

        invoice = await self.db.get(
            GSTInvoice,
            invoice_id,
        )

        if invoice is None:
            raise HTTPException(
                status_code=404,
                detail="GST invoice not found.",
            )

        if invoice.status == GSTInvoiceStatus.POSTED:
            raise HTTPException(
                status_code=409,
                detail="Invoice already posted.",
            )

        await self._ensure_period_open(
            invoice.invoice_date,
        )

        journal_service = JournalService(self.db)

        journal = await journal_service.create_gst_invoice_entry(
            invoice=invoice,
            posted_by=posted_by,
        )

        invoice.journal_entry_id = journal.id
        invoice.status = GSTInvoiceStatus.POSTED
        invoice.posted_by = posted_by

        await self.db.commit()
        await self.db.refresh(invoice)

        await write_audit_log(
            db=self.db,
            entity_type="gst_invoice",
            entity_id=str(invoice.id),
            action=AuditAction.CREATED,
            actor=posted_by,
            metadata={
                "invoice_number": invoice.invoice_number,
                "journal_entry": str(journal.id),
            },
        )

        return invoice

    # ==========================================================
    # GET INVOICE
    # ==========================================================

async def get_invoice(
        self,
        invoice_id: UUID,
    ) -> GSTInvoice:

        invoice = await self.db.get(
            GSTInvoice,
            invoice_id,
        )

        if invoice is None:
            raise HTTPException(
                status_code=404,
                detail="GST invoice not found.",
            )

        return invoice



    # ==========================================================
    # GST INVOICE QUERIES
    # ==========================================================

async def list_invoices(
        self,
        status: GSTInvoiceStatus | None = None,
    ) -> list[GSTInvoice]:
        """
        List GST invoices.
        """

        stmt = (
            select(GSTInvoice)
            .order_by(GSTInvoice.created_at.desc())
        )

        if status is not None:
            stmt = stmt.where(
                GSTInvoice.status == status
            )

        result = await self.db.execute(stmt)

        return result.scalars().all()

async def get_invoice_by_number(
        self,
        invoice_number: str,
    ) -> GSTInvoice:

        invoice = await self.db.scalar(
            select(GSTInvoice).where(
                GSTInvoice.invoice_number == invoice_number
            )
        )

        if invoice is None:
            raise HTTPException(
                status_code=404,
                detail="GST invoice not found.",
            )

        return invoice

    # ==========================================================
    # DRAFT MANAGEMENT
    # ==========================================================

async def cancel_invoice(
        self,
        invoice_id: UUID,
        cancelled_by: str,
    ) -> GSTInvoice:

        invoice = await self.get_invoice(invoice_id)

        if invoice.status == GSTInvoiceStatus.POSTED:
            raise HTTPException(
                status_code=409,
                detail="Posted invoices cannot be cancelled.",
            )

        invoice.status = GSTInvoiceStatus.CANCELLED

        await self.db.commit()
        await self.db.refresh(invoice)

        await write_audit_log(
            db=self.db,
            entity_type="gst_invoice",
            entity_id=str(invoice.id),
            action=AuditAction.UPDATED,
            actor=cancelled_by,
            metadata={
                "status": "cancelled",
            },
        )

        return invoice

async def delete_draft_invoice(
        self,
        invoice_id: UUID,
    ) -> None:

        invoice = await self.get_invoice(invoice_id)

        if invoice.status != GSTInvoiceStatus.DRAFT:
            raise HTTPException(
                status_code=409,
                detail="Only draft invoices can be deleted.",
            )

        await self.db.delete(invoice)
        await self.db.commit()

    # ==========================================================
    # GST RATE HELPERS
    # ==========================================================

async def list_active_rates(
        self,
    ) -> list[GSTRate]:

        result = await self.db.execute(
            select(GSTRate)
            .where(GSTRate.is_active.is_(True))
            .order_by(GSTRate.category_name)
        )

        return result.scalars().all()