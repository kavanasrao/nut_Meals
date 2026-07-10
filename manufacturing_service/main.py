"""
Manufacturing Service — FastAPI application entry point.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base
from app.db.database import engine
from app.db.database import get_db

from app.api.routes.raw_materials import router as raw_material_router
from app.api.routes.bom import router as bom_router
from app.api.routes.production_batches import router as production_batch_router
from app.api.routes.production_costs import router as production_cost_router
from app.api.routes.reports import router as reports_router
from app.api.routes.audit import router as audit_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s...", settings.SERVICE_NAME)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Manufacturing database initialized.")

    yield

    await engine.dispose()

    logger.info("%s stopped.", settings.SERVICE_NAME)


app = FastAPI(
    title="NutMeals Manufacturing Service",
    description="Manufacturing ERP Microservice",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# -------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# API Routes
# -------------------------------------------------------------------

app.include_router(raw_material_router, prefix="/api/v1")
app.include_router(bom_router, prefix="/api/v1")
app.include_router(production_batch_router, prefix="/api/v1")
app.include_router(production_cost_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")


# -------------------------------------------------------------------
# Health Check
# -------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Health"],
)
async def health_check():
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get(
    "/",
    tags=["Root"],
)
async def root():
    return {
        "message": "Manufacturing Service is running.",
        "docs": "/docs" if settings.DEBUG else "Disabled",
    }
