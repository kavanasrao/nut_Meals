"""Auth enhancement routes.

POST /api/v1/auth/forgot-password   — request a password reset email
POST /api/v1/auth/reset-password    — consume a reset token, set new password
POST /api/v1/auth/otp/request       — request an OTP via SMS or Email
POST /api/v1/auth/otp/verify        — verify OTP, get JWT tokens
POST /api/v1/auth/google            — Google Sign-In, get JWT tokens
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_access_token, create_refresh_token
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    MessageResponse,
    OtpRequest,
    OtpVerifyRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _tokens_for(user) -> TokenResponse:
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


# ── Forgot / Reset password ─────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset link via email",
)
async def forgot_password(
    body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    svc = AuthService(db)
    await svc.request_password_reset(body.email, ip_address=_client_ip(request))
    # Always return a generic success message to avoid leaking account existence.
    return MessageResponse(
        message="If an account exists for this email, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using a token from the forgot-password email",
)
async def reset_password(
    body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    svc = AuthService(db)
    success = await svc.reset_password(body.token, body.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token is invalid, expired, or already used",
        )
    return MessageResponse(message="Password has been reset successfully")


# ── OTP login ────────────────────────────────────────────────────────────────

@router.post(
    "/otp/request",
    response_model=MessageResponse,
    summary="Request an OTP via SMS or Email",
)
async def request_otp(body: OtpRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    svc = AuthService(db)
    await svc.request_otp(identifier=body.identifier, channel=body.channel)
    return MessageResponse(message=f"OTP sent via {body.channel}")


@router.post(
    "/otp/verify",
    response_model=TokenResponse,
    summary="Verify OTP and receive JWT tokens",
)
async def verify_otp(
    body: OtpVerifyRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    svc = AuthService(db)
    user = await svc.verify_otp(identifier=body.identifier, code=body.code)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP is invalid, expired, or exhausted",
        )
    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account blocked")
    await svc.send_login_alert(user, ip_address=_client_ip(request))
    return _tokens_for(user)


# ── Google social login ─────────────────────────────────────────────────────

@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in (or sign up) with Google",
)
async def google_login(
    body: GoogleLoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    svc = AuthService(db)
    user = await svc.google_login(body.id_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google credential"
        )
    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account blocked")
    await svc.send_login_alert(user, ip_address=_client_ip(request))
    return _tokens_for(user)
