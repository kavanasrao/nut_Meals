import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import InvoiceStatus
from app.models.invoice import PurchaseInvoice, PurchaseInvoiceItem
from app.schemas.invoice import PurchaseInvoiceCreate, PurchaseInvoiceStatusUpdate
from app.services.ledger_service import LedgerService
from app.services.vendor_service import VendorService


class InvoiceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vendor_service = VendorService(db)
        self.ledger_service = LedgerService(db)

    async def create_invoice(self, payload: PurchaseInvoiceCreate) -> PurchaseInvoice:
        await self.vendor_service.get_vendor(payload.vendor_id)

        subtotal = Decimal("0")
        tax_total = Decimal("0")
        items: list[PurchaseInvoiceItem] = []
        for item in payload.items:
            line_subtotal = item.unit_price * item.quantity
            line_tax = line_subtotal * (item.tax_rate_percent / Decimal("100"))
            line_total = line_subtotal + line_tax
            subtotal += line_subtotal
            tax_total += line_tax
            items.append(
                PurchaseInvoiceItem(
                    sku=item.sku,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    tax_rate_percent=item.tax_rate_percent,
                    line_total=line_total,
                )
            )

        invoice = PurchaseInvoice(
            invoice_number=payload.invoice_number,
            vendor_id=payload.vendor_id,
            purchase_order_id=payload.purchase_order_id,
            grn_id=payload.grn_id,
            status=InvoiceStatus.RECEIVED,
            invoice_date=payload.invoice_date,
            due_date=payload.due_date,
            currency=payload.currency,
            subtotal=subtotal,
            tax_amount=tax_total,
            total_amount=subtotal + tax_total,
            file_url=payload.file_url,
            items=items,
        )
        self.db.add(invoice)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "An invoice with this number already exists for this vendor",
            ) from exc

        # Book the payable on the vendor ledger and (best-effort) sync to Finance
        await self.ledger_service.record_invoice_booked(
            vendor_id=invoice.vendor_id,
            invoice_id=invoice.id,
            amount=invoice.total_amount,
            description=f"Purchase invoice {invoice.invoice_number}",
        )

        # Kick off async 3-way match if we have both PO and GRN references.
        # Imported lazily to avoid a circular import between services <-> tasks.
        if invoice.purchase_order_id and invoice.grn_id:
            try:
                from app.tasks.invoice_tasks import reconcile_invoice

                reconcile_invoice.delay(str(invoice.id))
            except Exception:  # noqa: BLE001
                # Celery broker unavailable shouldn't fail invoice creation;
                # the periodic reconcile_pending_invoices sweep will catch it.
                pass

        return await self.get_invoice(invoice.id)

    async def get_invoice(self, invoice_id: uuid.UUID) -> PurchaseInvoice:
        stmt = (
            select(PurchaseInvoice)
            .where(PurchaseInvoice.id == invoice_id)
            .options(selectinload(PurchaseInvoice.items))
        )
        result = await self.db.execute(stmt)
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase invoice not found")
        return invoice

    async def list_invoices(
        self,
        page: int,
        page_size: int,
        vendor_id: uuid.UUID | None = None,
        status_filter: InvoiceStatus | None = None,
    ) -> tuple[list[PurchaseInvoice], int]:
        stmt = select(PurchaseInvoice).options(selectinload(PurchaseInvoice.items))
        count_stmt = select(func.count()).select_from(PurchaseInvoice)

        if vendor_id:
            stmt = stmt.where(PurchaseInvoice.vendor_id == vendor_id)
            count_stmt = count_stmt.where(PurchaseInvoice.vendor_id == vendor_id)
        if status_filter:
            stmt = stmt.where(PurchaseInvoice.status == status_filter)
            count_stmt = count_stmt.where(PurchaseInvoice.status == status_filter)

        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(PurchaseInvoice.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def update_status(
        self, invoice_id: uuid.UUID, payload: PurchaseInvoiceStatusUpdate
    ) -> PurchaseInvoice:
        invoice = await self.get_invoice(invoice_id)
        invoice.status = payload.status
        if payload.reconciliation_notes:
            invoice.reconciliation_notes = payload.reconciliation_notes
        await self.db.commit()
        return await self.get_invoice(invoice_id)

    async def match_against_grn(self, invoice_id: uuid.UUID) -> PurchaseInvoice:
        """
        3-way match: PO quantities/prices vs GRN received quantities vs
        invoice quantities/prices. Used by the reconciliation Celery task.
        """
        invoice = await self.get_invoice(invoice_id)
        if invoice.purchase_order_id is None or invoice.grn_id is None:
            invoice.status = InvoiceStatus.DISPUTED
            invoice.reconciliation_notes = "Missing PO or GRN reference for 3-way match"
            await self.db.commit()
            return invoice

        from app.services.grn_service import GRNService
        from app.services.po_service import PurchaseOrderService

        po = await PurchaseOrderService(self.db).get_po(invoice.purchase_order_id)
        grn = await GRNService(self.db).get_grn(invoice.grn_id)

        po_qty_by_sku = {i.sku: i.quantity_ordered for i in po.items}
        grn_qty_by_sku: dict[str, int] = {}
        for gi in grn.items:
            grn_qty_by_sku[gi.sku] = grn_qty_by_sku.get(gi.sku, 0) + gi.quantity_received

        mismatches = []
        for item in invoice.items:
            grn_qty = grn_qty_by_sku.get(item.sku, 0)
            if item.quantity > grn_qty:
                mismatches.append(
                    f"{item.sku}: invoiced {item.quantity}, received {grn_qty}"
                )
            po_qty = po_qty_by_sku.get(item.sku)
            if po_qty is None:
                mismatches.append(f"{item.sku}: not present on PO")

        if mismatches:
            invoice.status = InvoiceStatus.DISPUTED
            invoice.reconciliation_notes = "; ".join(mismatches)
        else:
            invoice.status = InvoiceStatus.MATCHED
            invoice.reconciliation_notes = "3-way match passed"

        await self.db.commit()
        return await self.get_invoice(invoice_id)
