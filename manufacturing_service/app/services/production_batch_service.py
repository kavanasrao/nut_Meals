"""
Business logic for Production Batch Management.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_material import BatchMaterial
from app.models.bom_item import BOMItem
from app.models.production_batch import (
    BatchStatus,
    ProductionBatch,
)
from app.models.raw_material import RawMaterial
from app.schemas.production_batch import (
    ProductionBatchCreate,
)


class ProductionBatchService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # ==========================================================
    # CREATE BATCH
    # ==========================================================

    async def create(
        self,
        data: ProductionBatchCreate,
    ) -> ProductionBatch:

        batch = ProductionBatch(
            batch_number=data.batch_number,
            product_id=data.product_id,
            bom_id=data.bom_id,
            planned_quantity=data.planned_quantity,
            status=BatchStatus.PLANNED,
        )

        self.db.add(batch)

        await self.db.commit()

        await self.db.refresh(batch)

        return batch

    # ==========================================================
    # GET
    # ==========================================================

    async def get(
        self,
        batch_id,
    ) -> ProductionBatch | None:

        result = await self.db.execute(
            select(ProductionBatch).where(
                ProductionBatch.id == batch_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # LIST
    # ==========================================================

    async def list(self):

        result = await self.db.execute(
            select(ProductionBatch).order_by(
                ProductionBatch.created_at.desc()
            )
        )

        return list(result.scalars().all())

    # ==========================================================
    # START BATCH
    # ==========================================================

    async def start_batch(
        self,
        batch: ProductionBatch,
    ) -> ProductionBatch:

        if batch.status != BatchStatus.PLANNED:
            raise ValueError("Batch already started.")

        batch.status = BatchStatus.IN_PROGRESS
        batch.started_at = datetime.utcnow()

        await self._consume_materials(batch)

        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    # ==========================================================
    # COMPLETE BATCH
    # ==========================================================

    async def complete_batch(
        self,
        batch: ProductionBatch,
        produced_quantity,
    ) -> ProductionBatch:

        if batch.status != BatchStatus.IN_PROGRESS:
            raise ValueError("Batch is not in progress.")

        batch.status = BatchStatus.COMPLETED
        batch.produced_quantity = produced_quantity
        batch.completed_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    # ==========================================================
    # CANCEL
    # ==========================================================

    async def cancel_batch(
        self,
        batch: ProductionBatch,
    ) -> ProductionBatch:

        batch.status = BatchStatus.CANCELLED

        await self.db.commit()
        await self.db.refresh(batch)

        return batch

    # ==========================================================
    # CONSUME MATERIALS
    # ==========================================================

    async def _consume_materials(
        self,
        batch: ProductionBatch,
    ):

        result = await self.db.execute(
            select(BOMItem).where(
                BOMItem.bom_id == batch.bom_id
            )
        )

        bom_items = result.scalars().all()

        for item in bom_items:

            material = await self.db.get(
                RawMaterial,
                item.raw_material_id,
            )

            if material is None:
                raise ValueError(
                    "Raw material not found."
                )

            if material.current_stock < item.quantity:
                raise ValueError(
                    f"Insufficient stock for {material.name}"
                )

            material.current_stock -= item.quantity

            consumption = BatchMaterial(
                batch_id=batch.id,
                raw_material_id=material.id,
                planned_quantity=item.quantity,
                actual_quantity=item.quantity,
                wastage_quantity=0,
            )

            self.db.add(consumption)
            