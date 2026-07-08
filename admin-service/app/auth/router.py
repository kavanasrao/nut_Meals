"""Admin authentication routes.

POST /admin/auth/login    — exchange email+password for JWT pair
POST /admin/auth/refresh  — exchange refresh token for new access token
POST /admin/auth/logout   — client-side token invalidation (stateless)
GET  /admin/auth/me       — return current admin profile
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.models import AdminUser
from app.schemas.schemas import AdminUserOut, LoginRequest, RefreshRequest, TokenResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Admin Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Admin login — returns JWT access + refresh tokens",
)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(
        select(AdminUser).where(AdminUser.email == body.email)
    )
    admin: AdminUser | None = result.scalar_one_or_none()

    # Constant-time comparison prevents email enumeration
    if admin is None or not verify_password(body.password, admin.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is deactivated",
        )

    token_data = {
        "sub": str(admin.id),
        "email": admin.email,
        "role": admin.role.value,
    }
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=admin.role,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a valid refresh token",
)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    from jose import JWTError

    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is not a refresh token",
        )

    result = await db.execute(
        select(AdminUser).where(AdminUser.id == payload.get("sub"))
    )
    admin: AdminUser | None = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")

    token_data = {"sub": str(admin.id), "email": admin.email, "role": admin.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=admin.role,
    )


@router.get(
    "/me",
    response_model=AdminUserOut,
    summary="Get current admin profile",
)
async def me(admin: AdminUser = Depends(require_admin)) -> AdminUserOut:
    return AdminUserOut.model_validate(admin)


@router.post("/logout", summary="Logout (client-side token invalidation)")
async def logout() -> dict:
    # Stateless JWT — clients must discard the token.
    # For token blacklisting, add the JTI to Redis with TTL = token expiry.
    return {"message": "Logged out. Discard your tokens client-side."}
