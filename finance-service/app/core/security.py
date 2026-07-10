"""
Authentication (JWT, issued by the central Auth service) and RBAC for the
Finance service.

The Finance service does not issue tokens itself - it validates JWTs signed
by the platform Auth service (shared JWT_SECRET_KEY, injected via OCI Vault)
and enforces role checks locally. Roles are expected in the `roles` claim.
"""

from collections.abc import Iterable

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=True)


class Principal(BaseModel):
    subject: str
    roles: list[str] = []
    is_service_account: bool = False


class FinanceRole:
    """Role constants used across the Finance service."""

    VIEWER = "finance:viewer"  # read-only access to reports
    ACCOUNTANT = "finance:accountant"  # can create/post journal entries
    RECONCILER = "finance:reconciler"  # can trigger/resolve reconciliation
    ADMIN = "finance:admin"  # full access incl. chart of accounts management


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Principal:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return Principal(
        subject=payload["sub"],
        roles=payload.get("roles", []),
        is_service_account=payload.get("is_service_account", False),
    )


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory enforcing that the caller has at least one of
    `allowed_roles`, or the blanket ADMIN role.

    Usage: @router.post(..., dependencies=[Depends(require_roles(FinanceRole.ACCOUNTANT))])
    """

    async def _checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        allowed: Iterable[str] = {*allowed_roles, FinanceRole.ADMIN}
        if not allowed.intersection(principal.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {sorted(allowed)}",
            )
        return principal

    return _checker


async def enforce_https(request: Request) -> None:
    """Rejects plaintext HTTP in production; TLS termination normally happens at the
    ingress/load balancer, but this is a defense-in-depth check using the
    X-Forwarded-Proto header set by the LB."""
    if not settings.FORCE_HTTPS or settings.ENV == "local":
        return
    proto = request.headers.get("x-forwarded-proto", "https")
    if proto != "https":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required")
