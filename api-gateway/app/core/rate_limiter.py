"""Redis-backed sliding window rate limiter.

Uses the INCR + EXPIRE approach — lightweight, no Lua script required.
Each key holds a counter for a client IP within the current window.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


async def check_rate_limit(
    request: Request,
    *,
    max_requests: int | None = None,
) -> None:
    """
    Raise HTTP 429 if the client IP has exceeded the rate limit.

    Args:
        request: The incoming FastAPI request.
        max_requests: Override the default limit for this endpoint.
    """
    client_ip = request.client.host if request.client else "unknown"
    limit = max_requests or settings.RATE_LIMIT_MAX_REQUESTS
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    key = f"rate_limit:{client_ip}:{request.url.path}"

    redis = await get_redis()

    # Atomic increment
    count = await redis.incr(key)
    if count == 1:
        # First request in this window — set expiry
        await redis.expire(key, window)

    if count > limit:
        logger.warning("Rate limit exceeded: ip=%s path=%s count=%d", client_ip, request.url.path, count)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {limit} requests per {window}s.",
            headers={"Retry-After": str(window)},
        )
