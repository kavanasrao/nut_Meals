"""
Business logic for Bill of Materials (BOM).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bom import (
    BOM,
    BOMStatus,
)

from app.models.bom_item import (
    BOMItem,
)

from app.schemas.bom import (
    BOMCreate,
)


class BOMService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # ==========================================================
    # CREATE BOM
    # ==========================================================

    async def create(
        self,
        data: BOMCreate,
    ) -> BOM:

        bom = BOM(
            product_id=data.product_id,
            product_name=data.product_name,
            version=data.version,
            created_by=data.created_by,
            notes=data.notes,
            status=BOMStatus.DRAFT,
        )

        self.db.add(bom)

        await self.db.flush()

        for item in data.items:

            bom_item = BOMItem(
                bom_id=bom.id,
                raw_material_id=item.raw_material_id,
                quantity=item.quantity,
                wastage_percent=item.wastage_percent,
            )

            self.db.add(bom_item)

        await self.db.commit()

        await self.db.refresh(bom)

        return bom

    # ==========================================================
    # GET BOM
    # ==========================================================

    async def get(
        self,
        bom_id,
    ) -> BOM | None:

        result = await self.db.execute(
            select(BOM).where(
                BOM.id == bom_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # LIST BOMs
    # ==========================================================

    async def list(self):

        result = await self.db.execute(
            select(BOM).order_by(
                BOM.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # ACTIVATE BOM
    # ==========================================================

    async def activate(
        self,
        bom: BOM,
    ) -> BOM:

        bom.status = BOMStatus.ACTIVE

        await self.db.commit()

        await self.db.refresh(bom)

        return bom

    # ==========================================================
    # DEACTIVATE BOM
    # ==========================================================

    async def deactivate(
        self,
        bom: BOM,
    ) -> BOM:

        bom.status = BOMStatus.INACTIVE

        await self.db.commit()

        await self.db.refresh(bom)

        return bom

    # ==========================================================
    # DELETE
    # ==========================================================

    async def delete(
        self,
        bom: BOM,
    ):

        await self.db.delete(bom)

        await self.db.commit()
        