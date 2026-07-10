from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession,
    ) -> None:
        self.model = model
        self.db = db

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_by_id(self, obj_id: UUID) -> ModelType | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == obj_id,
                self.model.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        result = await self.db.execute(
            select(self.model)
            .where(self.model.is_deleted.is_(False))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update(
        self,
        db_obj: ModelType,
        data: dict[str, Any],
    ) -> ModelType:
        for key, value in data.items():
            setattr(db_obj, key, value)

        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def soft_delete(self, obj_id: UUID) -> bool:
        obj = await self.get_by_id(obj_id)

        if obj is None:
            return False

        obj.is_deleted = True
        obj.is_active = False

        await self.db.commit()

        return True

    async def hard_delete(self, obj_id: UUID) -> bool:
        result = await self.db.execute(
            delete(self.model).where(self.model.id == obj_id)
        )

        await self.db.commit()

        return result.rowcount > 0

    async def exists(self, obj_id: UUID) -> bool:
        return await self.get_by_id(obj_id) is not None
