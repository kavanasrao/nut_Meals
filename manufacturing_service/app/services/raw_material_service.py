"""
Business logic for Raw Material Management.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.raw_material import (
    RawMaterial,
)

from app.schemas.raw_material import (
    RawMaterialCreate,
    RawMaterialUpdate,
)


class RawMaterialService:

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
        data: RawMaterialCreate,
    ) -> RawMaterial:

        material = RawMaterial(**data.model_dump())

        self.db.add(material)

        await self.db.commit()

        await self.db.refresh(material)

        return material

    # ==========================================================
    # GET
    # ==========================================================

    async def get(
        self,
        material_id,
    ) -> RawMaterial | None:

        result = await self.db.execute(
            select(RawMaterial).where(
                RawMaterial.id == material_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # LIST
    # ==========================================================

    async def list(
        self,
    ) -> list[RawMaterial]:

        result = await self.db.execute(
            select(RawMaterial).order_by(
                RawMaterial.name
            )
        )

        return list(result.scalars().all())

    # ==========================================================
    # UPDATE
    # ==========================================================

    async def update(
        self,
        material: RawMaterial,
        data: RawMaterialUpdate,
    ) -> RawMaterial:

        for key, value in data.model_dump(
            exclude_unset=True
        ).items():

            setattr(material, key, value)

        await self.db.commit()

        await self.db.refresh(material)

        return material

    # ==========================================================
    # DELETE
    # ==========================================================

    async def delete(
        self,
        material: RawMaterial,
    ):

        await self.db.delete(material)

        await self.db.commit()

    # ==========================================================
    # STOCK
    # ==========================================================

    async def increase_stock(
        self,
        material: RawMaterial,
        quantity,
    ):

        material.current_stock += quantity

        await self.db.commit()

        return material

    async def decrease_stock(
        self,
        material: RawMaterial,
        quantity,
    ):

        if material.current_stock < quantity:

            raise ValueError(
                "Insufficient stock."
            )

        material.current_stock -= quantity

        await self.db.commit()

        return material
    