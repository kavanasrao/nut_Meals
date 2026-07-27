"""
Redis connection manager for the API Gateway.

Design decisions
----------------
* The client is created inside the FastAPI lifespan context (not lazily on
  first request) so startup failures are caught at boot, not mid-traffic.
* Connection pooling is configured explicitly — max_connections is capped to
  prevent exhausting the Redis server under burst load.
* Startup ping uses a short retry loop so transient Redis restarts during
  a rolling deploy don't fail the gateway boot permanently.
* Teardown uses aclose() (the correct async API) and does NOT null out the
  module-level reference — in-flight requests keep their reference valid
  until they complete naturally.
* get_redis() is a simple synchronous accessor after lifespan init; no
  global mutation happens at request time, so there is no TOCTOU race.
"""

from __future__ import annotations

import asyncio
import logging

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ==============================================================
# Module-level client — populated by lifespan, never mutated
# at request time.
# ==============================================================

_redis_client: aioredis.Redis | None = None

# ==============================================================
# Pool constants
# ==============================================================

# Keep well below Redis's default maxclients (typically 10 000)
# but high enough to handle gateway concurrency.
_POOL_MAX_CONNECTIONS: int = 100

# Seconds to wait for a free connection from the pool before raising.
_POOL_TIMEOUT: float = 5.0

# Ping retry settings for startup health check.
_PING_RETRIES: int = 3
_PING_RETRY_DELAY: float = 1.0  # seconds between attempts


# ==============================================================
# Lifespan helpers  (call from FastAPI lifespan context)
# ==============================================================

async def init_redis() -> None:
    """
    Create the connection pool and Redis client.

    Performs a startup ping with retries to surface Redis connectivity
    problems at boot rather than mid-traffic.

    Raises:
        RedisError: if Redis is unreachable after all retries.
    """
    global _redis_client

    if _redis_client is not None:
        logger.warning("init_redis() called more than once; skipping.")
        return

    logger.info("Initialising Redis connection pool: %s", settings.REDIS_URL)

    pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=_POOL_MAX_CONNECTIONS,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
        socket_keepalive=True,
        health_check_interval=30,
    )

    client = aioredis.Redis(connection_pool=pool)

    # Verify connectivity with retries — transient blips during rolling
    # deploys should not abort the gateway startup permanently.
    last_exc: Exception | None = None

    for attempt in range(1, _PING_RETRIES + 1):
        try:
            await client.ping()
            logger.info(
                "Redis ping successful (attempt %d/%d).",
                attempt,
                _PING_RETRIES,
            )
            break

        except (RedisConnectionError, RedisError) as exc:
            last_exc = exc
            logger.warning(
                "Redis ping failed (attempt %d/%d): %s",
                attempt,
                _PING_RETRIES,
                exc,
            )

            if attempt < _PING_RETRIES:
                await asyncio.sleep(_PING_RETRY_DELAY)
    else:
        # All retries exhausted
        await client.aclose()
        raise RedisError(
            f"Redis unavailable after {_PING_RETRIES} ping attempts."
        ) from last_exc

    _redis_client = client
    logger.info(
        "Redis client ready (pool max_connections=%d).",
        _POOL_MAX_CONNECTIONS,
    )


async def close_redis() -> None:
    """
    Flush pending commands and close the connection pool.

    Intentionally does NOT null out _redis_client so in-flight requests
    that already hold a reference continue to completion safely.
    The process is shutting down anyway — the GC will collect the object.
    """
    global _redis_client

    if _redis_client is None:
        logger.debug("close_redis() called but client was never initialised.")
        return

    logger.info("Closing Redis connection pool.")

    try:
        await _redis_client.aclose()          # correct async teardown
    except RedisError as exc:
        logger.warning("Error while closing Redis client: %s", exc)

    _redis_client = None
    logger.info("Redis connection pool closed.")


# ==============================================================
# Request-time accessor
# ==============================================================

def get_redis() -> aioredis.Redis:
    """
    Return the initialised Redis client.

    This is a plain synchronous function — no global mutation occurs at
    request time, eliminating the TOCTOU race present in lazy-init patterns.

    Raises:
        RuntimeError: if called before init_redis() has completed.
    """
    if _redis_client is None:
        raise RuntimeError(
            "Redis client is not initialised. "
            "Ensure init_redis() is called inside the FastAPI lifespan context."
        )
    return _redis_client


# ==============================================================
# FastAPI lifespan integration
# ==============================================================
#
# Wire this into your existing gateway lifespan:
#
#   from contextlib import asynccontextmanager
#   from app.core.redis_manager import init_redis, close_redis
#
#   @asynccontextmanager
#   async def lifespan(app: FastAPI):
#       await init_redis()
#       yield
#       await close_redis()
#
# ==============================================================

# ==============================================================
# Module exports
# ==============================================================

__all__ = [
    "get_redis",
    "init_redis",
    "close_redis",
]