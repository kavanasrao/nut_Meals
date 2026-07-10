from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer_audit import CustomerAudit
from app.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[CustomerAudit]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(CustomerAudit, db)

    async def get_by_customer_id(
        self,
        customer_id: UUID,
    ) -> list[CustomerAudit]:
        result = await self.db.execute(
            select(CustomerAudit)
            .where(
                CustomerAudit.customer_id == customer_id,
                CustomerAudit.is_deleted.is_(False),
            )
            .order_by(desc(CustomerAudit.created_at))
        )
        return result.scalars().all()

    async def get_by_action(
        self,
        action: str,
    ) -> list[CustomerAudit]:
        result = await self.db.execute(
            select(CustomerAudit)
            .where(
                CustomerAudit.action == action,
                CustomerAudit.is_deleted.is_(False),
            )
            .order_by(desc(CustomerAudit.created_at))
        )
        return result.scalars().all()

    async def get_by_entity(
        self,
        entity_name: str,
        entity_id: UUID,
    ) -> list[CustomerAudit]:
        result = await self.db.execute(
            select(CustomerAudit)
            .where(
                CustomerAudit.entity_name == entity_name,
                CustomerAudit.entity_id == entity_id,
                CustomerAudit.is_deleted.is_(False),
            )
            .order_by(desc(CustomerAudit.created_at))
        )
        return result.scalars().all()

    async def get_by_user(
        self,
        user_id: UUID,
    ) -> list[CustomerAudit]:
        result = await self.db.execute(
            select(CustomerAudit)
            .where(
                CustomerAudit.performed_by == user_id,
                CustomerAudit.is_deleted.is_(False),
            )
            .order_by(desc(CustomerAudit.created_at))
        )
        return result.scalars().all()

    async def get_recent(
        self,
        limit: int = 100,
    ) -> list[CustomerAudit]:
        result = await self.db.execute(
            select(CustomerAudit)
            .where(CustomerAudit.is_deleted.is_(False))
            .order_by(desc(CustomerAudit.created_at))
            .limit(limit)
        )
        return result.scalars().all()