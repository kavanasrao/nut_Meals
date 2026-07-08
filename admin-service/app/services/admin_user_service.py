"""Admin User management service.

Handles creation, listing, and deactivation of admin panel accounts.
Only superadmin can create new admins or promote roles.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.models import AdminRole, AdminUser
from app.schemas.schemas import AdminUserCreate, AdminUserUpdate

logger = logging.getLogger(__name__)


class AdminUserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, data: AdminUserCreate) -> AdminUser:
        # Check for duplicate email
        existing = await self.db.execute(
            select(AdminUser).where(AdminUser.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Admin with email '{data.email}' already exists")

        admin = AdminUser(
            id=uuid.uuid4(),
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=data.role,
            is_active=True,
        )
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        logger.info("Admin created: %s (%s)", admin.email, admin.role)
        return admin

    async def list_admins(self) -> list[AdminUser]:
        result = await self.db.execute(
            select(AdminUser).order_by(AdminUser.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, admin_id: str) -> AdminUser | None:
        try:
            aid = uuid.UUID(admin_id)
        except ValueError:
            return None
        result = await self.db.execute(select(AdminUser).where(AdminUser.id == aid))
        return result.scalar_one_or_none()

    async def update(self, admin_id: str, data: AdminUserUpdate) -> AdminUser | None:
        admin = await self.get(admin_id)
        if not admin:
            return None
        if data.full_name is not None:
            admin.full_name = data.full_name
        if data.role is not None:
            admin.role = data.role
        if data.is_active is not None:
            admin.is_active = data.is_active
        await self.db.commit()
        await self.db.refresh(admin)
        return admin

    async def deactivate(self, admin_id: str) -> AdminUser | None:
        return await self.update(admin_id, AdminUserUpdate(is_active=False))
