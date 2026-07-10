from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_note import CustomerNote
from app.repositories.base_repository import BaseRepository


class CustomerNoteRepository(BaseRepository[CustomerNote]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerNote, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerNote]:
        result = await self.db.execute(
            select(CustomerNote)
            .where(
                CustomerNote.customer_id == customer_id,
                CustomerNote.is_deleted.is_(False),
            )
            .order_by(desc(CustomerNote.created_at))
        )
        return result.scalars().all()

    async def get_internal_notes(
        self,
        customer_id: UUID,
    ) -> list[CustomerNote]:
        result = await self.db.execute(
            select(CustomerNote)
            .where(
                CustomerNote.customer_id == customer_id,
                CustomerNote.is_internal.is_(True),
                CustomerNote.is_deleted.is_(False),
            )
            .order_by(desc(CustomerNote.created_at))
        )
        return result.scalars().all()

    async def get_by_author(
        self,
        author_id: UUID,
    ) -> list[CustomerNote]:
        result = await self.db.execute(
            select(CustomerNote)
            .where(
                CustomerNote.created_by == author_id,
                CustomerNote.is_deleted.is_(False),
            )
            .order_by(desc(CustomerNote.created_at))
        )
        return result.scalars().all()