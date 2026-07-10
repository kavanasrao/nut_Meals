"""
Business logic for Production Cost Management.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_batch import ProductionBatch
from app.models.production_cost import ProductionCost
from app.schemas.production_cost import ProductionCostCreate


class ProductionCostService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # ==========================================================
    # CREATE COST RECORD
    # ==========================================================

    async def create(
        self,
        data: ProductionCostCreate,
    ) -> ProductionCost:

        total_cost = (
            data.material_cost
            + data.labour_cost
            + data.overhead_cost
        )

        cost = ProductionCost(
            batch_id=data.batch_id,
            material_cost=data.material_cost,
            labour_cost=data.labour_cost,
            overhead_cost=data.overhead_cost,
            total_cost=total_cost,
        )

        self.db.add(cost)

        await self.db.commit()

        await self.db.refresh(cost)

        return cost

    # ==========================================================
    # GET
    # ==========================================================

    async def get(
        self,
        cost_id,
    ) -> ProductionCost | None:

        result = await self.db.execute(
            select(ProductionCost).where(
                ProductionCost.id == cost_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # GET BY BATCH
    # ==========================================================

    async def get_by_batch(
        self,
        batch_id,
    ) -> ProductionCost | None:

        result = await self.db.execute(
            select(ProductionCost).where(
                ProductionCost.batch_id == batch_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # LIST
    # ==========================================================

    async def list(self):

        result = await self.db.execute(
            select(ProductionCost)
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # RECALCULATE
    # ==========================================================

    async def recalculate(
        self,
        cost: ProductionCost,
    ) -> ProductionCost:

        cost.total_cost = (
            cost.material_cost
            + cost.labour_cost
            + cost.overhead_cost
        )

        await self.db.commit()

        await self.db.refresh(cost)

        return cost

    # ==========================================================
    # COST PER UNIT
    # ==========================================================

    async def cost_per_unit(
        self,
        batch_id,
    ) -> Decimal:

        batch = await self.db.get(
            ProductionBatch,
            batch_id,
        )

        if batch is None:
            raise ValueError("Batch not found.")

        cost = await self.get_by_batch(
            batch_id,
        )

        if cost is None:
            raise ValueError("Production cost not found.")

        if batch.produced_quantity <= 0:
            return Decimal("0")

        return (
            cost.total_cost
            / batch.produced_quantity
        )

    # ==========================================================
    # DELETE
    # ==========================================================

    async def delete(
        self,
        cost: ProductionCost,
    ):

        await self.db.delete(cost)

        await self.db.commit()

        