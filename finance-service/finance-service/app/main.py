"""
Finance Service - FastAPI application entrypoint.

Handles double-entry ledger accounting, trial balance / P&L reporting,
payment gateway settlement reconciliation, and audit logging for
nut_Meals' microservices backend.
"""

import logging
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.security import enforce_https
from app.routers import audit, journal, ledger, reconciliation, reports

settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("finance_service")

app = FastAPI(
    title="nut_Meals Finance Service",
    description="Double-entry ledger, trial balance / P&L reporting, and settlement reconciliation.",
    version="1.0.0",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attaches a request ID for tracing and enforces HTTPS/logs timing."""
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
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
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak internal stack traces / DB errors to API consumers."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(ledger.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(enforce_https)])
app.include_router(journal.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(enforce_https)])
app.include_router(reports.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(enforce_https)])
app.include_router(reconciliation.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(enforce_https)])
app.include_router(audit.router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(enforce_https)])


@app.get("/healthz", tags=["Health"])
async def health_check():
    """Liveness/readiness probe target for Kubernetes/Docker Compose."""
    return {"status": "ok", "service": settings.SERVICE_NAME, "env": settings.ENV}
