"""
JWT-based authentication for the Cart/Checkout Extensions service.

This service does not own the customer identity/password store — that
lives in the core auth/customer-profile service. It only validates JWTs
issued by that upstream service (shared signing secret pulled from OCI
Vault) and exposes the decoded principal + roles for RBAC checks.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=True)


class Principal:
    """Represents the authenticated caller for the duration of a request."""

    def __init__(self, customer_id: str, roles: list[str]):
        self.customer_id = customer_id
        self.roles = roles

    def has_role(self, role: str) -> bool:
        return role in self.roles


def create_access_token(customer_id: str, roles: list[str], expires_minutes: int | None = None) -> str:
    """Issue a signed JWT. Used mainly in tests / local tooling — in
    production tokens are minted by the upstream auth service."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": customer_id, "roles": roles, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Principal:
    payload = decode_token(credentials.credentials)
    customer_id = payload.get("sub")
    roles = payload.get("roles", [])
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return Principal(customer_id=customer_id, roles=roles)
