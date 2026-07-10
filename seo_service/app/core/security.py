"""
JWT verification and RBAC enforcement for the SEO service.

The service trusts JWTs issued by the central Auth service, verified
with an RS256 public key pulled from OCI Vault at startup (never
committed to source or env files in plaintext for prod). HTTPS is
enforced at the ingress/load-balancer layer and re-checked here via
`X-Forwarded-Proto` as defense in depth.
"""
from __future__ import annotations

import enum
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()


class Role(str, enum.Enum):
    VIEWER = "viewer"          # read-only: sitemaps, structured data, AI export
    SEO_EDITOR = "seo_editor"  # manage redirects, canonicals, trigger resyncs
    ADMIN = "admin"            # full access, including audit log reads


class CurrentUser(BaseModel):
    subject: str
    role: Role
    raw_claims: dict


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "role"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


async def get_current_user(request: Request) -> CurrentUser:
    """Extract and verify the bearer JWT, enforcing HTTPS in production."""
    if settings.HTTPS_ONLY and settings.ENV == "production":
        proto = request.headers.get("x-forwarded-proto", "https")
        if proto != "https":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required"
            )

    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    token = auth_header.removeprefix("Bearer ").strip()
    claims = _decode_token(token)
    try:
        role = Role(claims["role"])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role"
        ) from exc
    return CurrentUser(subject=claims["sub"], role=role, raw_claims=claims)


def require_roles(*allowed: Role):
    """Dependency factory enforcing RBAC on a route."""

    async def _dependency(
        user: Annotated[CurrentUser, Depends(get_current_user)]
    ) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted to perform this action",
            )
        return user

    return _dependency
