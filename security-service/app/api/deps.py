"""
Shared FastAPI dependencies: JWT auth + RBAC permission enforcement.

The Auth service is the source of truth for identity and issues JWTs; the
Security Service *trusts* those JWTs (shared secret / JWKS) and layers its own
fine-grained permission checks on top via the RBAC tables owned here. This
lets Auth stay focused on "who are you" while Security owns "what can you do".
"""
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.rbac import Permission, Role, RolePermission, UserRoleBinding

settings = get_settings()


class CurrentUser:
    """Lightweight principal extracted from a validated JWT."""

    def __init__(self, user_id: str, roles: list[str], raw_claims: dict):
        self.user_id = user_id
        self.roles = roles
        self.raw_claims = raw_claims


async def get_current_user(request: Request) -> CurrentUser:
    """Validate the Bearer JWT on the request and return the principal.

    Raises 401 if the token is missing/invalid/expired. Signature is verified
    against JWT_SECRET (HS256), which is provisioned via OCI Vault in
    staging/production and shared with the Auth service.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = auth_header.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    roles = claims.get("roles", [])
    return CurrentUser(user_id=user_id, roles=roles, raw_claims=claims)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


async def user_has_permission(db: AsyncSession, user_id: str, permission_code: str) -> bool:
    """Check whether a user (by any of their bound roles) holds a permission.

    This re-checks against the live DB rather than trusting JWT role claims
    alone, so permission changes (e.g. revoking a role) take effect
    immediately without waiting for token expiry.
    """
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRoleBinding, UserRoleBinding.role_id == Role.id)
        .where(UserRoleBinding.user_id == user_id, Permission.code == permission_code)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


def require_permission(permission_code: str):
    """Dependency factory: enforces that the current user holds `permission_code`.

    Usage:
        @router.get("/waf/rules", dependencies=[Depends(require_permission("waf:read"))])
    """

    async def _checker(user: CurrentUserDep, db: DbDep) -> CurrentUser:
        allowed = await user_has_permission(db, user.user_id, permission_code)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission_code}",
            )
        return user

    return _checker
