"""JWT authentication utilities for the API Gateway.

The gateway is the single entry point that validates tokens.
Downstream services trust requests from the gateway without
re-validating JWTs (rely on internal network isolation instead).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Public endpoints that skip JWT validation
PUBLIC_PATHS: set[str] = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    
    # User authentication
    "/api/v1/users/register",
    "/api/v1/users/login",
    "/api/v1/users/refresh"


    # Webhook endpoints must NOT require auth (called by third parties)

    "/api/v1/payments/webhook",
}


def _decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(request: Request) -> dict[str, Any]:
    """
    Extract and validate Bearer token from the Authorization header.
    Returns the decoded JWT payload dict.
    """
    authorization: str = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    return _decode_token(token)


def require_auth(request: Request) -> dict[str, Any]:
    """FastAPI dependency — validates JWT, returns claims."""
    return get_current_user(request)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc")
