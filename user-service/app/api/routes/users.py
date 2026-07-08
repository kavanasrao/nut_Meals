"""User Service — REST API routes.

POST /api/v1/users/register      — create account
POST /api/v1/users/login         — get JWT pair
POST /api/v1/users/refresh       — refresh access token
GET  /api/v1/users/me            — current user profile
PATCH /api/v1/users/me           — update profile
POST /api/v1/users/me/change-password
GET  /api/v1/users               — list all users (internal/admin)
GET  /api/v1/users/stats         — aggregate counts (for admin dashboard)
GET  /api/v1/users/{user_id}     — get single user (internal/admin)
PATCH /api/v1/users/{user_id}/block
PATCH /api/v1/users/{user_id}/unblock
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_active_user
from app.core.db import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserListResponse,
    UserOut,
    UserProfileUpdate,
    UserStatsResponse,
)
from app.services.user_service import UserService
from jose import JWTError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


# ── Auth ──────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserOut:
    svc = UserService(db)
    try:
        user = await svc.register(body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Login and receive JWT tokens")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    svc = UserService(db)
    user = await svc.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked",
        )
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a refresh token")

    svc = UserService(db)
    user = await svc.get_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account blocked")

    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


# ── Own profile ───────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut, summary="Get current user profile")
async def get_me(user: User = Depends(require_active_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut, summary="Update current user profile")
async def update_me(
    body: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> UserOut:
    svc = UserService(db)
    updated = await svc.update_profile(user, body)
    return UserOut.model_validate(updated)


@router.post("/me/change-password", summary="Change password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> dict:
    svc = UserService(db)
    success = await svc.change_password(user, body)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    return {"message": "Password changed successfully"}


# ── Internal / admin routes ───────────────────────────────────────────────────

@router.get("/stats", response_model=UserStatsResponse, summary="User aggregate stats (internal)")
async def user_stats(db: AsyncSession = Depends(get_db)) -> UserStatsResponse:
    svc = UserService(db)
    return await svc.get_stats()


@router.get("/", response_model=UserListResponse, summary="List users (internal/admin)")
async def list_users(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    svc = UserService(db)
    users, total = await svc.list_users(limit=limit, offset=offset)
    return UserListResponse(
        users=[UserOut.model_validate(u) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{user_id}", response_model=UserOut, summary="Get user by ID (internal/admin)")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)) -> UserOut:
    svc = UserService(db)
    user = await svc.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.patch("/{user_id}/block", response_model=UserOut, summary="Block a user")
async def block_user(user_id: str, db: AsyncSession = Depends(get_db)) -> UserOut:
    svc = UserService(db)
    user = await svc.block(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.patch("/{user_id}/unblock", response_model=UserOut, summary="Unblock a user")
async def unblock_user(user_id: str, db: AsyncSession = Depends(get_db)) -> UserOut:
    svc = UserService(db)
    user = await svc.unblock(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)
