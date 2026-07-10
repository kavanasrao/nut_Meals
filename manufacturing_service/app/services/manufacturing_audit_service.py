"""
Business logic for Manufacturing Audit.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manufacturing_audit import ManufacturingAudit


class ManufacturingAuditService:

    def __init__(
        self,
        db: AsyncSession,
    ):
        self.db = db

    # ==========================================================
    # CREATE AUDIT
    # ==========================================================

    async def create(
        self,
        audit: ManufacturingAudit,
    ) -> ManufacturingAudit:

        self.db.add(audit)

        await self.db.commit()

        await self.db.refresh(audit)

        return audit

    # ==========================================================
    # GET
    # ==========================================================

    async def get(
        self,
        audit_id,
    ) -> ManufacturingAudit | None:

        result = await self.db.execute(
            select(ManufacturingAudit).where(
                ManufacturingAudit.id == audit_id
            )
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # LIST
    # ==========================================================

    async def list(self):

        result = await self.db.execute(
            select(ManufacturingAudit).order_by(
                ManufacturingAudit.created_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # FILTER BY ENTITY
    # ==========================================================

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
    ) -> list[ManufacturingAudit]:

        result = await self.db.execute(
            select(ManufacturingAudit).where(
                ManufacturingAudit.entity_type == entity_type,
                ManufacturingAudit.entity_id == entity_id,
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # FILTER BY USER
    # ==========================================================

    async def get_by_user(
        self,
        user_id: str,
    ) -> list[ManufacturingAudit]:

        result = await self.db.execute(
            select(ManufacturingAudit).where(
                ManufacturingAudit.performed_by == user_id
            )
        )

        return list(
            result.scalars().all()
        )

    # ==========================================================
    # DELETE
    # ==========================================================

    async def delete(
        self,
        audit: ManufacturingAudit,
    ):

        await self.db.delete(audit)

        await self.db.commit()