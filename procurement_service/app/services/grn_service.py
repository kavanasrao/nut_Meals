import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import GRNStatus, PurchaseOrderStatus
from app.models.grn import GoodsReceiptNote, GRNItem
from app.models.purchase_order import PurchaseOrderItem
from app.schemas.grn import GRNCreate
from app.services.po_service import PurchaseOrderService


def _generate_grn_number() -> str:
    return f"GRN-{uuid.uuid4().hex[:10].upper()}"


class GRNService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.po_service = PurchaseOrderService(db)

    async def create_grn(self, payload: GRNCreate, received_by: uuid.UUID) -> GoodsReceiptNote:
        po = await self.po_service.get_po(payload.purchase_order_id)
        if po.status not in (
            PurchaseOrderStatus.APPROVED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Goods can only be received against an approved purchase order",
            )

        po_items_by_id: dict[uuid.UUID, PurchaseOrderItem] = {i.id: i for i in po.items}

        grn_items = []
        for item in payload.items:
            po_item = po_items_by_id.get(item.purchase_order_item_id)
            if po_item is None:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"PO item {item.purchase_order_item_id} does not belong to this PO",
                )
            remaining = po_item.quantity_ordered - po_item.quantity_received
            if item.quantity_received > remaining:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    f"Cannot receive {item.quantity_received} units of {item.sku}; "
                    f"only {remaining} remaining on the PO",
                )
            po_item.quantity_received += item.quantity_received
            grn_items.append(
                GRNItem(
                    purchase_order_item_id=item.purchase_order_item_id,
                    sku=item.sku,
                    quantity_received=item.quantity_received,
                    quantity_rejected=item.quantity_rejected,
                    rejection_reason=item.rejection_reason,
                )
            )

        grn = GoodsReceiptNote(
            grn_number=_generate_grn_number(),
            purchase_order_id=payload.purchase_order_id,
            status=GRNStatus.CONFIRMED,
            received_by=received_by,
            remarks=payload.remarks,
            items=grn_items,
        )
        self.db.add(grn)
        await self.db.commit()

        await self.po_service.recompute_receipt_status(payload.purchase_order_id)
        return await self.get_grn(grn.id)

    async def get_grn(self, grn_id: uuid.UUID) -> GoodsReceiptNote:
        stmt = (
            select(GoodsReceiptNote)
            .where(GoodsReceiptNote.id == grn_id)
            .options(selectinload(GoodsReceiptNote.items))
        )
        result = await self.db.execute(stmt)
        grn = result.scalar_one_or_none()
        if grn is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "GRN not found")
        return grn

    async def list_grns_for_po(self, po_id: uuid.UUID) -> list[GoodsReceiptNote]:
        stmt = (
            select(GoodsReceiptNote)
            .where(GoodsReceiptNote.purchase_order_id == po_id)
            .options(selectinload(GoodsReceiptNote.items))
            .order_by(GoodsReceiptNote.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
