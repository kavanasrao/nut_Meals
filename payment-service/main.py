"""Payment Service — FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.payments import router as payments_router
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
    logger.info("Starting %s (provider=%s)", settings.SERVICE_NAME, settings.PAYMENT_PROVIDER)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await close_redis()
    await engine.dispose()
    logger.info("%s stopped", settings.SERVICE_NAME)


app = FastAPI(
    title="Nutmeals — Payment Service",
    version="1.0.0",
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

app.include_router(payments_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "provider": settings.PAYMENT_PROVIDER,
    }
