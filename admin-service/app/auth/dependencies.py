"""FastAPI dependencies for admin authentication and role-based access control.

Usage in routes:
    @router.get("/something")
    async def endpoint(admin = Depends(require_admin)):
        ...

    @router.delete("/something")
    async def superadmin_endpoint(admin = Depends(require_superadmin)):
        ...
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models.models import AdminRole, AdminUser

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """
    Decode the Bearer JWT and load the AdminUser from the DB.
    Raises HTTP 401 if the token is missing, invalid, or expired.
    Raises HTTP 403 if the admin account is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise credentials_exception

    # Reject refresh tokens used as access tokens
    if payload.get("type") != "access":
        raise credentials_exception

    admin_id: str | None = payload.get("sub")
    if not admin_id:
        raise credentials_exception

    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin: AdminUser | None = result.scalar_one_or_none()

    if admin is None:
        raise credentials_exception

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is deactivated",
        )

    return admin


async def require_admin(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Allow any active admin (admin OR superadmin)."""
    return admin


async def require_superadmin(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """Allow only superadmin role."""
    if admin.role != AdminRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return admin
