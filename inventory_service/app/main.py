"""
Inventory Service — FastAPI entrypoint.

Runs as an independent microservice within the nut_Meals backend, with its
own database, migrations, and deployment pipeline. See README.md.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import batches, bom, items, reports, reservations, warehouses
from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inventory")

app = FastAPI(
    title="nut_Meals Inventory Service",
    description="Warehouses, Bill of Materials, batch production, and stock reservations.",
    version="1.0.0",
    docs_url="/docs" if settings.ENV != "production" else None,
)

# Enforce HTTPS in staging/production (local dev typically runs behind a
# TLS-terminating proxy already, so this is disabled via env var locally).
if settings.FORCE_HTTPS and settings.ENV == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.nutmeals.example"],  # tighten per-environment via env config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_request_logger(request: Request, call_next):
    """Lightweight request audit log (method, path, actor if present)."""
    response = await call_next(request)
    logger.info(
        "request",
        extra={"method": request.method, "path": request.url.path, "status": response.status_code},
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["health"])
async def health_check():
    """Liveness/readiness probe for orchestration (k8s/ECS/Docker Compose)."""
    return {"status": "ok", "service": settings.SERVICE_NAME, "env": settings.ENV}


app.include_router(warehouses.router, prefix=settings.API_V1_PREFIX)
app.include_router(items.router, prefix=settings.API_V1_PREFIX)
app.include_router(bom.router, prefix=settings.API_V1_PREFIX)
app.include_router(batches.router, prefix=settings.API_V1_PREFIX)
app.include_router(reservations.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)
