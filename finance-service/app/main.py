"""
Finance Service - FastAPI application entrypoint.

Handles double-entry ledger accounting, trial balance / P&L reporting,
payment gateway settlement reconciliation, GST, refunds,
credit notes, audit logging, and accounting period locking
for nut_Meals' microservices backend.
"""

import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.security import enforce_https
from app.routers import (
    audit,
    audit_lock,
    credit_note,
    gst,
    journal,
    ledger,
    reconciliation,
    refund,
    reports,
)

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("finance_service")

app = FastAPI(
    title="nut_Meals Finance Service",
    description=(
        "Double-entry ledger, GST, refunds, credit notes, "
        "trial balance / P&L reporting, settlement reconciliation, "
        "and audit management."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach request ID, enforce tracing, and log request duration."""

    request_id = request.headers.get(
        "x-request-id",
        str(uuid.uuid4()),
    )

    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000

    response.headers["x-request-id"] = request_id

    logger.info(
        "%s %s -> %s (%.1fms) [request_id=%s]",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    """Never expose internal stack traces to API consumers."""

    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ==========================================================
# Core Accounting
# ==========================================================

app.include_router(
    ledger.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

app.include_router(
    journal.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

app.include_router(
    reports.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

app.include_router(
    reconciliation.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

app.include_router(
    audit.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

# ==========================================================
# GST Management
# ==========================================================

app.include_router(
    gst.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

# ==========================================================
# Credit Notes
# ==========================================================

app.include_router(
    credit_note.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

# ==========================================================
# Refunds
# ==========================================================

app.include_router(
    refund.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)

# ==========================================================
# Accounting Period Lock
# ==========================================================

app.include_router(
    audit_lock.router,
    prefix=settings.API_V1_PREFIX,
    dependencies=[Depends(enforce_https)],
)


@app.get("/healthz", tags=["Health"])
async def health_check():
    """Liveness/readiness probe."""

    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "env": settings.ENV,
    }
