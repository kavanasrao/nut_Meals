"""
Order Service — FastAPI application entry point.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.orders import router as orders_router
from app.api.routes.returns import router as returns_router

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
    """
    Application startup/shutdown lifecycle.
    """

    logger.info(
        "Starting %s (%s)",
        settings.SERVICE_NAME,
        settings.ENVIRONMENT,
    )

    # Create tables (replace with Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized.")

    yield

    await close_redis()

    await engine.dispose()

    logger.info("%s stopped.", settings.SERVICE_NAME)


app = FastAPI(
    title="NutMeals Order Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# API Routes
# ==========================================================

app.include_router(
    orders_router,
    prefix="/api/v1",
)

app.include_router(
    returns_router,
    prefix="/api/v1",
)

# ==========================================================
# Health Check
# ==========================================================


@app.get(
    "/health",
    tags=["Health"],
)
async def health():

    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():

    return {
        "service": "NutMeals Order Service",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "disabled",
    }