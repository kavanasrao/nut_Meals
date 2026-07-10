"""
Authentication and RBAC for admin endpoints.

Admins authenticate against the central admin-service, which issues a
short-lived RS256 JWT. This service only *verifies* that token (using
the public key distributed via OCI Vault) and enforces role-based access
control locally -- it does not issue tokens itself.
"""
import uuid
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.config import get_settings
from app.models.common import AdminRole

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=True)


class AdminPrincipal(BaseModel):
    """The authenticated admin user, extracted from the verified JWT."""

    admin_id: uuid.UUID
    email: str
    roles: list[AdminRole]


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return payload


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AdminPrincipal:
    """FastAPI dependency: verifies the bearer JWT and returns the admin principal."""
    payload = _decode_token(credentials.credentials)
    try:
        return AdminPrincipal(
            admin_id=uuid.UUID(payload["sub"]),
            email=payload.get("email", ""),
            roles=[AdminRole(r) for r in payload.get("roles", [])],
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token claims"
        ) from exc


def require_roles(*allowed_roles: AdminRole):
    """
    Dependency factory enforcing RBAC. Usage:

        @router.post("/returns/{id}/approve", dependencies=[Depends(require_roles(
            AdminRole.SUPER_ADMIN, AdminRole.SUPPORT_ADMIN
        ))])
    """

    async def _check(admin: AdminPrincipal = Depends(get_current_admin)) -> AdminPrincipal:
        if AdminRole.SUPER_ADMIN in admin.roles:
            return admin  # super admin bypasses granular checks
        if not _has_any_role(admin.roles, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action",
            )
        return admin

    return _check


def _has_any_role(admin_roles: Iterable[AdminRole], allowed: Iterable[AdminRole]) -> bool:
    return bool(set(admin_roles) & set(allowed))
