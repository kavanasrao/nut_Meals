"""
Business logic for Lot Traceability.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lot_traceability import LotTraceability


class LotTraceabilityService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # ==========================================================
    # CREATE
    # ==========================================================

    async def create(
        self,
        lot: LotTraceability,
    ) -> LotTraceability:

        self.db.add(lot)

        await self.db.commit()

        await self.db.refresh(lot)

        return lot

    # ==========================================================
    # GET
    # ==========================================================

    async def get(
        self,
        traceability_id,
    ) -> LotTraceability | None:

        result = await self.db.execute(
            select(LotTraceability).where(
                LotTraceability.id == traceability_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # GET BY BATCH
    # ==========================================================

    async def get_batch_traceability(
        self,
        batch_id,
    ) -> list[LotTraceability]:

        result = await self.db.execute(
            select(LotTraceability).where(
                LotTraceability.batch_id == batch_id
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # GET BY RAW MATERIAL
    # ==========================================================

    async def get_material_history(
        self,
        raw_material_id,
    ) -> list[LotTraceability]:

        result = await self.db.execute(
            select(LotTraceability).where(
                LotTraceability.raw_material_id == raw_material_id
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # GET BY LOT NUMBER
    # ==========================================================

    async def get_by_internal_lot(
        self,
        lot_number: str,
    ) -> LotTraceability | None:

        result = await self.db.execute(
            select(LotTraceability).where(
                LotTraceability.internal_lot_number == lot_number
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # LIST
    # ==========================================================

    async def list(self):

        result = await self.db.execute(
            select(LotTraceability)
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # DELETE
    # ==========================================================

    async def delete(
        self,
        lot: LotTraceability,
    ):

        await self.db.delete(lot)

        await self.db.commit()

    # ==========================================================
    # PRODUCT RECALL
    # ==========================================================

    async def trace_product_recall(
        self,
        supplier_lot_number: str,
    ) -> list[LotTraceability]:

        """
        Returns all production batches
        that consumed a supplier lot.

        Used during food recalls.
        """

        result = await self.db.execute(
            select(LotTraceability).where(
                LotTraceability.supplier_lot_number
                == supplier_lot_number
            )
        )

        return list(
            result.scalars().all()
        )
    
    