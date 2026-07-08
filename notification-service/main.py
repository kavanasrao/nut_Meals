"""Notification Service — FastAPI application entry point.

Starts the Redis Pub/Sub consumer as a background asyncio task
alongside the HTTP server so both can share the event loop.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import Base, engine
from app.core.redis import close_redis
from app.events.consumer import run_consumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _consumer_task

    # ── Startup ────────────────────────────────────────────────────────
    logger.info(
        "Starting %s (whatsapp_provider=%s)",
        settings.SERVICE_NAME,
        settings.WHATSAPP_PROVIDER,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Launch the Redis consumer as a background task
    _consumer_task = asyncio.create_task(run_consumer())
    logger.info("Redis consumer task started")

    yield

    # ── Shutdown ───────────────────────────────────────────────────────
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass

    await close_redis()
    await engine.dispose()
    logger.info("%s stopped", settings.SERVICE_NAME)


app = FastAPI(
    title="Nutmeals — Notification Service",
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


@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "whatsapp_provider": settings.WHATSAPP_PROVIDER,
        "subscribed_channels": settings.SUBSCRIBED_CHANNELS,
    }
