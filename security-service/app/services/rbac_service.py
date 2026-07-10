"""
RBAC management service: roles, permissions, and user<->role bindings.
"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Permission, Role, UserRoleBinding
from app.schemas.rbac import PermissionCreate, RoleCreate


class RbacService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Permissions -------------------------------------------------------

    async def create_permission(self, payload: PermissionCreate) -> Permission:
        permission = Permission(**payload.model_dump())
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def list_permissions(self, service: Optional[str] = None) -> list[Permission]:
        stmt = select(Permission)
        if service:
            stmt = stmt.where(Permission.service == service)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # --- Roles ---------------------------------------------------------------

    async def create_role(self, payload: RoleCreate) -> Role:
        role = Role(name=payload.name, description=payload.description)
        if payload.permission_codes:
            stmt = select(Permission).where(Permission.code.in_(payload.permission_codes))
            result = await self.db.execute(stmt)
            role.permissions = list(result.scalars().all())
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role, attribute_names=["permissions"])
        return role

    async def list_roles(self) -> list[Role]:
        stmt = select(Role).options(selectinload(Role.permissions))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name).options(selectinload(Role.permissions))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_role_permissions(self, role_id: uuid.UUID, permission_codes: list[str]) -> Role:
        role = await self.db.get(Role, role_id, options=[selectinload(Role.permissions)])
        if role is None:
            raise ValueError(f"No role with id {role_id}")
        stmt = select(Permission).where(Permission.code.in_(permission_codes))
        result = await self.db.execute(stmt)
        role.permissions = list(result.scalars().all())
        await self.db.commit()
        await self.db.refresh(role, attribute_names=["permissions"])
        return role

    # --- Bindings --------------------------------------------------------------

    async def bind_user_role(self, user_id: str, role_name: str, granted_by: str) -> UserRoleBinding:
        role = await self.get_role_by_name(role_name)
        if role is None:
            raise ValueError(f"No role named '{role_name}'")

        binding = UserRoleBinding(user_id=user_id, role_id=role.id, granted_by=granted_by)
        self.db.add(binding)
        await self.db.commit()
        await self.db.refresh(binding, attribute_names=["role"])
        return binding

    async def list_user_bindings(self, user_id: str) -> list[UserRoleBinding]:
        stmt = (
            select(UserRoleBinding)
            .where(UserRoleBinding.user_id == user_id)
            .options(selectinload(UserRoleBinding.role).selectinload(Role.permissions))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def revoke_binding(self, binding_id: uuid.UUID) -> bool:
        binding = await self.db.get(UserRoleBinding, binding_id)
        if binding is None:
            return False
        await self.db.delete(binding)
        await self.db.commit()
        return True

    async def user_roles(self, user_id: str) -> list[str]:
        bindings = await self.list_user_bindings(user_id)
        return [b.role.name for b in bindings]
