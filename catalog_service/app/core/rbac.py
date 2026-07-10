"""
RBAC (role-based access control) for the Catalog Service.

Roles:
  - viewer       : read-only access to public catalog/SEO/redirect data
  - customer     : viewer + can submit reviews
  - catalog_admin: full CRUD on products/categories/SEO/redirects
  - moderator    : can approve/reject reviews
  - superadmin    : all permissions

JWTs are issued by the central Auth/Identity service; this service only
verifies and authorizes based on claims (`sub`, `role`).
"""
from enum import Enum
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


class Role(str, Enum):
    VIEWER = "viewer"
    CUSTOMER = "customer"
    CATALOG_ADMIN = "catalog_admin"
    MODERATOR = "moderator"
    SUPERADMIN = "superadmin"


class CurrentUser(BaseModel):
    id: str
    role: Role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    """Decode & validate the bearer JWT, returning the authenticated principal."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    sub = payload.get("sub")
    role = payload.get("role")
    if not sub or role not in Role.__members__.values() and role not in [r.value for r in Role]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token claims")

    return CurrentUser(id=sub, role=Role(role))


def require_roles(*allowed: Role):
    """FastAPI dependency factory: raises 403 unless current user has an allowed role."""

    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role == Role.SUPERADMIN:
            return user
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted to perform this action",
            )
        return user

    return checker
