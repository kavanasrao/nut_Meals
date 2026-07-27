"""Pydantic schemas for auth-enhancement flows: forgot/reset password,
OTP login, and Google social login."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.user import TokenResponse

__all__ = [
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "OtpRequest",
    "OtpVerifyRequest",
    "GoogleLoginRequest",
    "TokenResponse",
    "MessageResponse",
]


class MessageResponse(BaseModel):
    message: str


# ── Forgot / Reset password ─────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8, max_length=128)


# ── OTP login ────────────────────────────────────────────────────────────────

class OtpRequest(BaseModel):
    """Request an OTP be sent via SMS or Email. Exactly one of email/phone
    must be supplied, matching the chosen channel."""
    channel: Literal["sms", "email"]
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?\d{7,15}$")

    @model_validator(mode="after")
    def _check_identifier(self) -> "OtpRequest":
        if self.channel == "email" and not self.email:
            raise ValueError("email is required when channel is 'email'")
        if self.channel == "sms" and not self.phone:
            raise ValueError("phone is required when channel is 'sms'")
        return self

    @property
    def identifier(self) -> str:
        return self.email if self.channel == "email" else self.phone  # type: ignore[return-value]


class OtpVerifyRequest(BaseModel):
    channel: Literal["sms", "email"]
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?\d{7,15}$")
    code: str = Field(..., min_length=4, max_length=8)

    @model_validator(mode="after")
    def _check_identifier(self) -> "OtpVerifyRequest":
        if self.channel == "email" and not self.email:
            raise ValueError("email is required when channel is 'email'")
        if self.channel == "sms" and not self.phone:
            raise ValueError("phone is required when channel is 'sms'")
        return self

    @property
    def identifier(self) -> str:
        return self.email if self.channel == "email" else self.phone  # type: ignore[return-value]


# ── Google Social Login ─────────────────────────────────────────────────────

class GoogleLoginRequest(BaseModel):
    """`id_token` is the Google-issued JWT credential from Google Identity
    Services (One Tap / Sign in with Google) on the client."""
    id_token: str = Field(..., min_length=10)
