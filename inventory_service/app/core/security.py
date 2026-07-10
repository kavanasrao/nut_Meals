"""
Authentication & RBAC.

JWTs are issued by the central Auth service; Inventory only verifies them.
The signing key is pulled from OCI Vault at startup and injected as the
JWT_SECRET_KEY env var (see README.md "Secrets Management").
"""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=True)


@dataclass
class CurrentUser:
    subject: str
    roles: list[str]


class Roles:
    ADMIN = "inventory:admin"
    MANAGER = "inventory:manager"      # can manage warehouses, BOMs, batches
    OPERATOR = "inventory:operator"    # can execute transfers, adjustments
    ORDERS_SERVICE = "inventory:orders_service"  # service-to-service, reservations only
    VIEWER = "inventory:viewer"


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    payload = decode_token(credentials.credentials)
    return CurrentUser(subject=payload.get("sub", "unknown"), roles=payload.get("roles", []))


def require_roles(*allowed_roles: str):
    """FastAPI dependency factory enforcing RBAC on an endpoint."""

    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not set(allowed_roles).intersection(user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return checker
