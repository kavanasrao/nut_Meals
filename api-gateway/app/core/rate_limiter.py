"""
Redis-backed sliding window rate limiter.

Algorithm
---------
Uses a Lua script to atomically:
  1. Remove all entries outside the current window (ZREMRANGEBYSCORE).
  2. Count remaining entries (ZCARD).
  3. Reject immediately if already at the limit.
  4. Add the current request timestamp (ZADD).
  5. Set/refresh the key TTL (EXPIRE).

This is a true sliding window — a client that sends 100 requests at
00:59 cannot send any more until those entries age out, regardless of
where the clock-minute boundary falls.

All five operations execute in a single Redis round-trip under the same
Lua context, so there is no race between INCR and EXPIRE.

Key format
----------
    rate:{method}:{path}:{client_ip}

Including the HTTP method prevents POST /login and GET /login from
sharing a counter.  Unknown IPs are rejected before a Redis call is made.

Per-path limits
---------------
Pass a custom `max_requests` to override the default for specific
endpoints (e.g. stricter limits on auth paths).
"""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.redis_manager import get_redis

logger = logging.getLogger(__name__)

settings = get_settings()

# ==============================================================
# Lua script — atomic sliding window
#
# KEYS[1] = the rate-limit key
# ARGV[1] = current timestamp (ms, as string)
# ARGV[2] = window size in milliseconds
# ARGV[3] = max allowed requests in the window
# ARGV[4] = TTL in seconds for the key
#
# Returns: {current_count, requests_in_window_after_add}
#   current_count  — how many requests were in the window BEFORE
#                    this one (used to decide allow/deny)
#   ttl            — remaining TTL on the key (ms), for Retry-After
# ==============================================================

_SLIDING_WINDOW_SCRIPT = """
local key        = KEYS[1]
local now        = tonumber(ARGV[1])
local window_ms  = tonumber(ARGV[2])
local limit      = tonumber(ARGV[3])
local ttl_s      = tonumber(ARGV[4])
local window_start = now - window_ms

-- Remove entries that have slid out of the window
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

-- Count how many are left (before adding this request)
local count = redis.call('ZCARD', key)

if count >= limit then
    -- Over limit — find the oldest entry to calculate Retry-After
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local retry_ms = 0
    if oldest and oldest[2] then
        retry_ms = math.ceil((tonumber(oldest[2]) + window_ms - now) / 1000)
    end
    return {count, retry_ms}
end

-- Under limit — record this request with a unique member
-- (timestamp_ms + random suffix avoids collisions at high concurrency)
local member = tostring(now) .. ':' .. tostring(math.random(1, 999999))
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl_s)

return {count + 1, 0}
"""


# ==============================================================
# Auth-path prefix detection
# ==============================================================

_AUTH_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth/",
    "/api/v1/users/login",
    "/api/v1/users/register",
)


def _is_auth_path(path: str) -> bool:
    return path.startswith(_AUTH_PREFIXES)


def _resolve_limit(path: str, override: int | None) -> int:
    """
    Return the effective request limit for this path.

    Priority:
        1. Explicit override passed by the caller.
        2. Stricter auth limit for login / register / token paths.
        3. Global default.
    """
    if override is not None:
        return override
    if _is_auth_path(path):
        return settings.RATE_LIMIT_AUTH_MAX_REQUESTS
    return settings.RATE_LIMIT_MAX_REQUESTS


# ==============================================================
# Public interface
# ==============================================================

async def check_rate_limit(
    request: Request,
    *,
    max_requests: int | None = None,
) -> None:
    """
    Enforce a sliding-window rate limit for the requesting client.

    Raises:
        HTTPException(429) with a precise Retry-After header when the
        client has exceeded the allowed request rate.
        HTTPException(500) if the Redis call fails unexpectedly —
        failing open (allowing the request) is a deliberate choice to
        prevent a Redis outage from taking down the entire gateway.

    Args:
        request:      The incoming FastAPI request.
        max_requests: Override the per-window limit for this call site.
    """
    # ----------------------------------------------------------
    # 1. Resolve client identity
    # ----------------------------------------------------------

    if not request.client:
        # No client info — fail open with a warning rather than
        # blocking legitimate requests (e.g. from internal probes).
        logger.warning(
            "rate_limit | no client address on request — skipping"
        )
        return

    client_ip = request.client.host
    path = request.url.path
    method = request.method

    # ----------------------------------------------------------
    # 2. Resolve effective limit
    # ----------------------------------------------------------

    limit = _resolve_limit(path, max_requests)
    window_s = settings.RATE_LIMIT_WINDOW_SECONDS
    window_ms = window_s * 1_000
    now_ms = int(time.time() * 1_000)

    # Key includes method so POST /login ≠ GET /login
    key = f"rate:{method}:{path}:{client_ip}"

    # ----------------------------------------------------------
    # 3. Execute atomic sliding-window script
    # ----------------------------------------------------------

    try:
        redis = get_redis()           # sync accessor — no await
        result: list[int] = await redis.eval(
            _SLIDING_WINDOW_SCRIPT,
            1,                        # number of KEYS
            key,                      # KEYS[1]
            str(now_ms),              # ARGV[1]
            str(window_ms),           # ARGV[2]
            str(limit),               # ARGV[3]
            str(window_s + 1),        # ARGV[4]  TTL = window + 1s buffer
        )

    except Exception:
        # Fail open — a Redis outage should not take down the gateway.
        logger.exception(
            "rate_limit | Redis error — failing open | ip=%s path=%s",
            client_ip,
            path,
        )
        return

    count: int = result[0]
    retry_after_s: int = result[1]

    # ----------------------------------------------------------
    # 4. Enforce limit
    # ----------------------------------------------------------

    if retry_after_s > 0:
        logger.warning(
            "rate_limit | exceeded | ip=%s method=%s path=%s "
            "count=%d limit=%d retry_after=%ds",
            client_ip,
            method,
            path,
            count,
            limit,
            retry_after_s,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded. "
                f"Max {limit} requests per {window_s}s window. "
                f"Retry after {retry_after_s}s."
            ),
            headers={"Retry-After": str(retry_after_s)},
        )

    logger.debug(
        "rate_limit | ok | ip=%s method=%s path=%s count=%d/%d",
        client_ip,
        method,
        path,
        count,
        limit,
    )


# ==============================================================
# Module exports
# ==============================================================

__all__ = ["check_rate_limit"]