"""API Gateway — FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes.gateway import close_http_client, router as gateway_router
from app.core.config import settings
from app.core.redis import close_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.SERVICE_NAME, settings.ENVIRONMENT)
    yield
    await close_redis()
    await close_http_client()
    logger.info("%s stopped", settings.SERVICE_NAME)


app = FastAPI(
    title="Nutmeals — API Gateway",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Security middleware ───────────────────────────────────────────────────────
# In production, restrict allowed hosts to your actual domain
if settings.ENVIRONMENT != "local":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["nutmeals.in", "*.nutmeals.in"])

cors_origins = (
    [o.strip() for o in settings.CORS_ORIGINS.split(",")]
    if settings.CORS_ORIGINS != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(gateway_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}
