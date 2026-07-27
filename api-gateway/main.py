"""
API Gateway — FastAPI application entry point.

Startup order
-------------
1. Logging configured
2. Redis pool initialised (rate limiter depends on it)
3. HTTP client initialised (proxy depends on it)
4. Middleware applied (CORS, TrustedHost)
5. Routers mounted
6. App ready to serve

Shutdown order  (reverse of startup)
--------------------------------------
1. HTTP client closed  (stop accepting new upstream connections)
2. Redis pool closed   (flush pending commands)
"""

from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes.gateway import init_http_client, close_http_client, router as gateway_router
from app.core.config import get_settings
from app.core.redis_manager import init_redis, close_redis

# ==============================================================
# Logging
# ==============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ==============================================================
# Settings  (single call — lru_cache ensures one instance)
# ==============================================================

settings = get_settings()

# ==============================================================
# Lifespan
# ==============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage startup and shutdown of shared resources.

    Resources are initialised in dependency order and torn down
    in reverse — HTTP client first, Redis last.
    """
    logger.info(
        "Starting %s | env=%s | debug=%s",
        settings.SERVICE_NAME,
        settings.ENVIRONMENT,
        settings.is_debug_mode,
    )

    # 1. Redis — must be up before any request hits the rate limiter
    await init_redis()

    # 2. HTTP client — must be up before any request is proxied
    await init_http_client()

    logger.info("%s is ready to serve requests.", settings.SERVICE_NAME)

    yield  # ← application runs here

    # Shutdown (reverse order)
    logger.info("Shutting down %s ...", settings.SERVICE_NAME)

    # 1. HTTP client first — stop new upstream connections
    await close_http_client()

    # 2. Redis last — rate limiter may still be active during proxy teardown
    await close_redis()

    logger.info("%s stopped cleanly.", settings.SERVICE_NAME)


# ==============================================================
# Application
# ==============================================================

app = FastAPI(
    title="NutMeals — API Gateway",
    version="1.0.0",
    # Use is_debug_mode — guards against DEBUG=True leaking into production
    docs_url="/docs" if settings.is_debug_mode else None,
    redoc_url="/redoc" if settings.is_debug_mode else None,
    openapi_url="/openapi.json" if settings.is_debug_mode else None,
    lifespan=lifespan,
)

# ==============================================================
# Middleware
# Note: middleware is applied in reverse order of registration —
# the last registered runs first on incoming requests.
# ==============================================================

# -- Trusted Host -----------------------------------------------
# Reject requests with a spoofed Host header.
# Applied in staging + production (not local/development where
# requests come from localhost / docker-compose service names).
_STRICT_ENVIRONMENTS = {"staging", "production"}

if settings.ENVIRONMENT in _STRICT_ENVIRONMENTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "nutmeals.in",
            "*.nutmeals.in",
            "api.nutmeals.in",
        ],
    )

# -- CORS -------------------------------------------------------
# Use the parsed list from settings — no manual split needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],   # expose correlation ID to clients
)

# ==============================================================
# Routes
# ==============================================================

app.include_router(gateway_router)

# ==============================================================
# Health check
# Registered directly on app (not via gateway router) so it
# never gets proxied to a downstream service.
# ==============================================================

@app.get("/health", tags=["Health"], include_in_schema=True)
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
    }