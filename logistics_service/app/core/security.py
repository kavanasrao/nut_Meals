"""
JWT-based authentication and RBAC for Logistics Service endpoints.

The service trusts JWTs issued by the central auth/identity service (shared
public key, RS256). Every request must carry a Bearer token; the `roles`
claim is checked against per-endpoint requirements via `require_roles`.
HTTPS is enforced at the ingress/load-balancer level and re-checked here
via the `X-Forwarded-Proto` header as defense in depth.
"""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: str
    roles: list[str]


async def enforce_https(request: Request) -> None:
    if not settings.enforce_https:
        return
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    if proto != "https" and settings.environment != "development":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required")


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_public_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": bool(settings.jwt_public_key)},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    return Principal(user_id=payload.get("sub", "unknown"), roles=payload.get("roles", []))


def require_roles(*allowed_roles: str):
    """Dependency factory enforcing RBAC on a route."""

    async def _checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not set(principal.roles) & set(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {allowed_roles}",
            )
        return principal

    return _checker
