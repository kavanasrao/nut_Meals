"""
Manufacturing Reporting Service.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_batch import (
    BatchStatus,
    ProductionBatch,
)
from app.models.raw_material import RawMaterial


class ReportingService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    async def dashboard(self):

        total_batches = await self.db.scalar(
            select(func.count(ProductionBatch.id))
        )

        completed_batches = await self.db.scalar(
            select(func.count(ProductionBatch.id)).where(
                ProductionBatch.status == BatchStatus.COMPLETED
            )
        )

        running_batches = await self.db.scalar(
            select(func.count(ProductionBatch.id)).where(
                ProductionBatch.status == BatchStatus.IN_PROGRESS
            )
        )

        total_materials = await self.db.scalar(
            select(func.count(RawMaterial.id))
        )

        return {
            "total_batches": total_batches or 0,
            "completed_batches": completed_batches or 0,
            "running_batches": running_batches or 0,
            "total_raw_materials": total_materials or 0,
        }

    # ==========================================================
    # LOW STOCK
    # ==========================================================

    async def low_stock_materials(self):

        result = await self.db.execute(
            select(RawMaterial).where(
                RawMaterial.current_stock <=
                RawMaterial.reorder_level
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # BATCH HISTORY
    # ==========================================================

    async def batch_history(self):

        result = await self.db.execute(
            select(ProductionBatch).order_by(
                ProductionBatch.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # ACTIVE BATCHES
    # ==========================================================

    async def active_batches(self):

        result = await self.db.execute(
            select(ProductionBatch).where(
                ProductionBatch.status == BatchStatus.IN_PROGRESS
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # COMPLETED BATCHES
    # ==========================================================

    async def completed_batches(self):

        result = await self.db.execute(
            select(ProductionBatch).where(
                ProductionBatch.status == BatchStatus.COMPLETED
            )
        )

        return list(
            result.scalars().all()
        )
    