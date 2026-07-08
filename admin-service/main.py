"""Admin Service — FastAPI application entry point.

All admin routes live under /admin/* prefix.
Authentication is JWT-based; roles enforced per route.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    admin_users,
    audit_logs,
    config,
    dashboard,
    delivery,
    meals,
    notifications,
    orders,
    payment,
    users,
)
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.db import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

ADMIN_PREFIX = "/admin"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────
    logger.info("Starting %s (env=%s)", settings.SERVICE_NAME, settings.ENVIRONMENT)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")
    yield
    # ── Shutdown ───────────────────────────────────────────────────────
    await engine.dispose()
    logger.info("%s stopped", settings.SERVICE_NAME)


app = FastAPI(
    title="Nutmeals — Admin Service",
    description=(
        "Backend-For-Frontend admin panel. "
        "Manage users, orders, meals, delivery, payments, and notifications."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to admin frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth_router,          prefix=f"{ADMIN_PREFIX}/auth")
app.include_router(dashboard.router,     prefix=ADMIN_PREFIX)
app.include_router(admin_users.router,   prefix=ADMIN_PREFIX)
app.include_router(users.router,         prefix=ADMIN_PREFIX)
app.include_router(orders.router,        prefix=ADMIN_PREFIX)
app.include_router(meals.router,         prefix=ADMIN_PREFIX)
app.include_router(delivery.router,      prefix=ADMIN_PREFIX)
app.include_router(payment.router,       prefix=ADMIN_PREFIX)
app.include_router(notifications.router, prefix=ADMIN_PREFIX)
app.include_router(config.router,        prefix=ADMIN_PREFIX)
app.include_router(audit_logs.router,    prefix=ADMIN_PREFIX)


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}
