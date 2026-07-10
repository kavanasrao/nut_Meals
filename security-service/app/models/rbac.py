"""
RBAC models.

These mirror/extend identity data owned by the Auth service. The Security
Service does NOT own user identities — it owns fine-grained *authorization
policy* (roles, permissions, and role->permission bindings) that every other
service can query or that gets embedded as JWT claims by the Auth service.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoleName(str, enum.Enum):
    """Baseline roles across nut_meals. Additional custom roles may be added
    via the `roles` table without requiring an enum migration, since
    `Role.name` also accepts arbitrary strings for tenant-specific roles."""

    ADMIN = "admin"
    FINANCE = "finance"
    LOGISTICS = "logistics"
    SUPPORT = "support"
    SECURITY_AUDITOR = "security_auditor"
    CUSTOMER = "customer"


class Role(Base):
    """A named role, e.g. 'finance', that groups a set of permissions."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )
    bindings: Mapped[list["UserRoleBinding"]] = relationship(back_populates="role")


class Permission(Base):
    """A single fine-grained permission, e.g. 'orders:refund' or 'compliance:export'.

    Convention: `<service>:<action>` (e.g. `payments:capture`, `inventory:adjust`,
    `compliance:read`, `waf:manage_rules`). Services check permissions by name,
    not by role, so a role's composition can change without breaking callers.
    """

    __tablename__ = "permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    roles: Mapped[list["Role"]] = relationship(
        "Role", secondary="role_permissions", back_populates="permissions"
    )


class RolePermission(Base):
    """Join table binding roles <-> permissions (many-to-many)."""

    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class UserRoleBinding(Base):
    """Assigns a role to a user (user identity owned by Auth service, referenced
    here by opaque user_id UUID/string, e.g. Auth service's `sub` claim)."""

    __tablename__ = "user_role_bindings"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"))
    granted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    role: Mapped["Role"] = relationship(back_populates="bindings")
