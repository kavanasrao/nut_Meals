import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import PurchaseOrderStatus
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.services.vendor_service import VendorService
from app.schemas.purchase_order import (
    PurchaseOrderApproval,
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
)


def _generate_po_number() -> str:
    return f"PO-{uuid.uuid4().hex[:10].upper()}"


class PurchaseOrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vendor_service = VendorService(db)

    async def create_po(
        self, payload: PurchaseOrderCreate, created_by: uuid.UUID
    ) -> PurchaseOrder:
        await self.vendor_service.get_vendor(payload.vendor_id)  # 404 if invalid

        subtotal = Decimal("0")
        tax_total = Decimal("0")
        items: list[PurchaseOrderItem] = []
        for item in payload.items:
            line_subtotal = item.unit_price * item.quantity_ordered
            line_tax = line_subtotal * (item.tax_rate_percent / Decimal("100"))
            line_total = line_subtotal + line_tax
            subtotal += line_subtotal
            tax_total += line_tax
            items.append(
                PurchaseOrderItem(
                    sku=item.sku,
                    description=item.description,
                    quantity_ordered=item.quantity_ordered,
                    unit_price=item.unit_price,
                    tax_rate_percent=item.tax_rate_percent,
                    line_total=line_total,
                )
            )

        po = PurchaseOrder(
            po_number=_generate_po_number(),
            vendor_id=payload.vendor_id,
            status=PurchaseOrderStatus.PENDING_APPROVAL,
            expected_delivery_date=payload.expected_delivery_date,
            currency=payload.currency,
            subtotal=subtotal,
            tax_amount=tax_total,
            total_amount=subtotal + tax_total,
            notes=payload.notes,
            created_by=created_by,
            items=items,
        )
        self.db.add(po)
        await self.db.commit()
        return await self.get_po(po.id)

    async def get_po(self, po_id: uuid.UUID) -> PurchaseOrder:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po_id)
            .options(selectinload(PurchaseOrder.items))
        )
        result = await self.db.execute(stmt)
        po = result.scalar_one_or_none()
        if po is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
        return po

    async def get_po_by_number(self, po_number: str) -> PurchaseOrder:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.po_number == po_number)
            .options(selectinload(PurchaseOrder.items))
        )
        result = await self.db.execute(stmt)
        po = result.scalar_one_or_none()
        if po is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
        return po

    async def list_pos(
        self,
        page: int,
        page_size: int,
        vendor_id: uuid.UUID | None = None,
        status_filter: PurchaseOrderStatus | None = None,
    ) -> tuple[list[PurchaseOrder], int]:
        stmt = select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        count_stmt = select(func.count()).select_from(PurchaseOrder)

        if vendor_id:
            stmt = stmt.where(PurchaseOrder.vendor_id == vendor_id)
            count_stmt = count_stmt.where(PurchaseOrder.vendor_id == vendor_id)
        if status_filter:
            stmt = stmt.where(PurchaseOrder.status == status_filter)
            count_stmt = count_stmt.where(PurchaseOrder.status == status_filter)

        total = (await self.db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(PurchaseOrder.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def update_po(
        self, po_id: uuid.UUID, payload: PurchaseOrderUpdate
    ) -> PurchaseOrder:
        po = await self.get_po(po_id)
        if po.status not in (PurchaseOrderStatus.DRAFT, PurchaseOrderStatus.PENDING_APPROVAL):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Only draft or pending-approval purchase orders can be edited",
            )
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(po, field, value)
        await self.db.commit()
        return await self.get_po(po_id)

    async def approve_or_reject_po(
        self, po_id: uuid.UUID, payload: PurchaseOrderApproval, approver_id: uuid.UUID
    ) -> PurchaseOrder:
        po = await self.get_po(po_id)
        if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Purchase order is in status '{po.status.value}' and cannot be approved/rejected",
            )
        if payload.approve:
            po.status = PurchaseOrderStatus.APPROVED
            po.approved_by = approver_id
            po.approved_at = datetime.now(timezone.utc).isoformat()
        else:
            po.status = PurchaseOrderStatus.REJECTED
            po.rejection_reason = payload.rejection_reason
        await self.db.commit()
        return await self.get_po(po_id)

    async def cancel_po(self, po_id: uuid.UUID) -> PurchaseOrder:
        po = await self.get_po(po_id)
        if po.status in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CLOSED):
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Cannot cancel a received/closed purchase order"
            )
        po.status = PurchaseOrderStatus.CANCELLED
        await self.db.commit()
        return await self.get_po(po_id)

    async def recompute_receipt_status(self, po_id: uuid.UUID) -> PurchaseOrder:
        """Called after a GRN is confirmed to roll PO status forward."""
        po = await self.get_po(po_id)
        total_ordered = sum(i.quantity_ordered for i in po.items)
        total_received = sum(i.quantity_received for i in po.items)

        if total_received <= 0:
            new_status = po.status
        elif total_received < total_ordered:
            new_status = PurchaseOrderStatus.PARTIALLY_RECEIVED
        else:
            new_status = PurchaseOrderStatus.RECEIVED

        if new_status != po.status:
            po.status = new_status
            await self.db.commit()
        return await self.get_po(po_id)
