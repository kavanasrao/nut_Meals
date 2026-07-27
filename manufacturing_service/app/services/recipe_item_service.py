"""
Recipe Item service.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recipe_item import RecipeItem
from app.schemas.recipe_item import (
    RecipeItemCreate,
    RecipeItemUpdate,
)


class RecipeItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recipe_item(
        self,
        item_in: RecipeItemCreate,
    ) -> RecipeItem:

        item = RecipeItem(**item_in.model_dump())

        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def get_recipe_item(
        self,
        item_id: UUID,
    ) -> RecipeItem | None:

        result = await self.db.execute(
            select(RecipeItem).where(
                RecipeItem.id == item_id
            )
        )

        return result.scalar_one_or_none()

    async def list_recipe_items(
        self,
        recipe_id: UUID,
    ) -> list[RecipeItem]:

        result = await self.db.execute(
            select(RecipeItem)
            .where(RecipeItem.recipe_id == recipe_id)
            .order_by(RecipeItem.sequence)
        )

        return list(result.scalars().all())

    async def update_recipe_item(
        self,
        item_id: UUID,
        item_in: RecipeItemUpdate,
    ) -> RecipeItem | None:

        item = await self.get_recipe_item(item_id)

        if item is None:
            return None

        update_data = item_in.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(item, key, value)

        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def delete_recipe_item(
        self,
        item_id: UUID,
    ) -> bool:

        item = await self.get_recipe_item(item_id)

        if item is None:
            return False

        await self.db.delete(item)
        await self.db.commit()

        return True

    async def reorder_recipe_items(
        self,
        recipe_id: UUID,
        item_orders: list[tuple[UUID, int]],
    ) -> list[RecipeItem]:

        items = await self.list_recipe_items(recipe_id)

        item_map = {
            item.id: item
            for item in items
        }

        for item_id, sequence in item_orders:
            if item_id in item_map:
                item_map[item_id].sequence = sequence

        await self.db.commit()

        for item in item_map.values():
            await self.db.refresh(item)

        return list(item_map.values())

    async def total_recipe_items(
        self,
        recipe_id: UUID,
    ) -> int:

        items = await self.list_recipe_items(recipe_id)

        return len(items)
    