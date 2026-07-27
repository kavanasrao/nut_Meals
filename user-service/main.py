"""User Service — FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  registers all ORM models on Base.metadata
from app.api.routes.addresses import router as addresses_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.integrations import router as integrations_router
from app.api.routes.internal import router as internal_router
from app.api.routes.preferences import router as preferences_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.db import Base, engine
from app.core.redis import close_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.SERVICE_NAME, settings.ENVIRONMENT)
    if settings.ENVIRONMENT == "local":
        # Convenience for local dev only — staging/production schemas are
        # managed exclusively via `alembic upgrade head` (see Dockerfile /
        # CI pipeline), never via create_all.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured (local dev create_all)")
    yield
    await close_redis()
    await engine.dispose()
    logger.info("%s stopped", settings.SERVICE_NAME)


app = FastAPI(
    title="Nutmeals — User Service",
    version="1.1.0",
    description=(
        "Accounts, authentication (password/OTP/Google), profiles, saved "
        "addresses, preferences, and audit logs for the Nutmeals platform."
    ),
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(addresses_router, prefix="/api/v1")
app.include_router(preferences_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}
