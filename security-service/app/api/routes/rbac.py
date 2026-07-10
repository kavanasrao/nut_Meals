"""
RBAC management API.

- `/rbac/permissions` — catalog of fine-grained permissions each service exposes.
- `/rbac/roles` — role definitions and their permission sets.
- `/rbac/bindings` — user<->role assignment.
- `/rbac/check` — the endpoint other services call to answer "can user X do Y?"
  (also embeddable as a library call via app.services.rbac_service for
  same-process checks, as app.api.deps.require_permission does internally).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DbDep, require_permission, user_has_permission
from app.schemas.rbac import (
    AccessCheckRequest,
    AccessCheckResponse,
    PermissionCreate,
    PermissionOut,
    RoleCreate,
    RoleOut,
    RoleUpdatePermissions,
    UserRoleBindingCreate,
    UserRoleBindingOut,
)
from app.services.rbac_service import RbacService

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.post(
    "/permissions",
    response_model=PermissionOut,
    dependencies=[Depends(require_permission("rbac:manage"))],
)
async def create_permission(payload: PermissionCreate, db: DbDep):
    """Register a new fine-grained permission for a service. Requires `rbac:manage`."""
    service = RbacService(db)
    return await service.create_permission(payload)


@router.get("/permissions", response_model=list[PermissionOut], dependencies=[Depends(require_permission("rbac:read"))])
async def list_permissions(db: DbDep, service_name: str | None = None):
    """List permissions, optionally filtered by owning service. Requires `rbac:read`."""
    service = RbacService(db)
    return await service.list_permissions(service_name)


@router.post("/roles", response_model=RoleOut, dependencies=[Depends(require_permission("rbac:manage"))])
async def create_role(payload: RoleCreate, db: DbDep):
    """Create a role with an initial permission set. Requires `rbac:manage`."""
    service = RbacService(db)
    return await service.create_role(payload)


@router.get("/roles", response_model=list[RoleOut], dependencies=[Depends(require_permission("rbac:read"))])
async def list_roles(db: DbDep):
    """List all roles and their permissions. Requires `rbac:read`."""
    service = RbacService(db)
    return await service.list_roles()


@router.patch(
    "/roles/{role_id}/permissions",
    response_model=RoleOut,
    dependencies=[Depends(require_permission("rbac:manage"))],
)
async def set_role_permissions(role_id: uuid.UUID, payload: RoleUpdatePermissions, db: DbDep):
    """Replace a role's permission set entirely. Requires `rbac:manage`."""
    service = RbacService(db)
    try:
        return await service.set_role_permissions(role_id, payload.permission_codes)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/bindings",
    response_model=UserRoleBindingOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("rbac:manage"))],
)
async def bind_user_role(payload: UserRoleBindingCreate, db: DbDep, user: CurrentUserDep):
    """Grant a role to a user. Requires `rbac:manage`."""
    service = RbacService(db)
    try:
        return await service.bind_user_role(payload.user_id, payload.role_name, granted_by=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/bindings/{user_id}",
    response_model=list[UserRoleBindingOut],
    dependencies=[Depends(require_permission("rbac:read"))],
)
async def list_user_bindings(user_id: str, db: DbDep):
    """List roles bound to a given user. Requires `rbac:read`."""
    service = RbacService(db)
    return await service.list_user_bindings(user_id)


@router.delete(
    "/bindings/{binding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("rbac:manage"))],
)
async def revoke_binding(binding_id: uuid.UUID, db: DbDep):
    """Revoke a role grant from a user. Requires `rbac:manage`."""
    service = RbacService(db)
    found = await service.revoke_binding(binding_id)
    if not found:
        raise HTTPException(status_code=404, detail="Binding not found")


@router.post("/check", response_model=AccessCheckResponse)
async def check_access(payload: AccessCheckRequest, db: DbDep):
    """Ask 'can this user perform this permission?' -- called by other services
    at authorization time (e.g. Orders service checking `orders:refund`
    before processing a refund). No permission gate on this endpoint itself:
    it's a read-only check every internal service needs to call."""
    allowed = await user_has_permission(db, payload.user_id, payload.permission_code)
    service = RbacService(db)
    roles = await service.user_roles(payload.user_id) if allowed else []
    return AccessCheckResponse(allowed=allowed, roles=roles)
