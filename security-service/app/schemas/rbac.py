"""Pydantic schemas for RBAC (roles, permissions, bindings)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    description: Optional[str] = None
    service: str


class PermissionCreate(BaseModel):
    code: str = Field(..., max_length=128, description="e.g. 'orders:refund'")
    description: Optional[str] = None
    service: str = Field(..., max_length=64)


class RoleCreate(BaseModel):
    name: str = Field(..., max_length=64)
    description: Optional[str] = None
    permission_codes: list[str] = Field(default_factory=list)


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_system_role: bool
    created_at: datetime
    permissions: list[PermissionOut] = Field(default_factory=list)


class RoleUpdatePermissions(BaseModel):
    permission_codes: list[str]


class UserRoleBindingCreate(BaseModel):
    user_id: str = Field(..., max_length=128)
    role_name: str = Field(..., max_length=64)


class UserRoleBindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: str
    role: RoleOut
    granted_by: Optional[str] = None
    created_at: datetime


class AccessCheckRequest(BaseModel):
    """Payload other services POST to ask: 'can this user do this?'"""

    user_id: str
    permission_code: str


class AccessCheckResponse(BaseModel):
    allowed: bool
    roles: list[str] = Field(default_factory=list)
