"""User Service — FastAPI dependencies.

get_current_user: validates JWT and returns the User ORM object.
require_active_user: ensures the user is not blocked.
verify_internal_service: validates the shared internal-service token used
    by other nut_meals microservices (Order, Logistics, CRM) to call this
    service's server-to-server endpoints. Distinct from user JWT auth —
    there is no "current user" on these calls, only a trusted caller.
"""
from __future__ import annotations

import hmac
import logging

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise exc
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise exc

    if payload.get("type") != "access":
        raise exc

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise exc
    return user


async def require_active_user(user: User = Depends(get_current_user)) -> User:
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked. Contact support.",
        )
    return user


async def verify_internal_service(
    x_internal_service_token: str | None = Header(default=None),
) -> None:
    """Gate service-to-service endpoints (see app/api/routes/internal.py)
    behind the shared `INTERNAL_SERVICE_TOKEN`. Uses a constant-time
    comparison to avoid leaking the secret via timing side-channels."""
    if not x_internal_service_token or not hmac.compare_digest(
        x_internal_service_token, settings.INTERNAL_SERVICE_TOKEN
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid internal service credentials",
        )
