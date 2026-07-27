import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import engine
from app.routers import grn, invoices, purchase_orders, vendors

settings = get_settings()

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(settings.SERVICE_NAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s in %s mode", settings.SERVICE_NAME, settings.ENV)
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Procurement Service",
    description="Vendor, Purchase Order, GRN, and Invoice management for nut_meals",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS — restrict to known origins in production via env-driven config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.nutmeals.example"] if settings.ENV == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"message": exc.detail, "status_code": exc.status_code}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"message": "Validation failed", "details": exc.errors()}},
    )


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """Checks DB connectivity — used by k8s/compose readiness probes."""
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ready"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"DB not reachable: {exc}")


app.include_router(vendors.router, prefix=settings.API_V1_PREFIX)
app.include_router(purchase_orders.router, prefix=settings.API_V1_PREFIX)
app.include_router(grn.router, prefix=settings.API_V1_PREFIX)
app.include_router(invoices.router, prefix=settings.API_V1_PREFIX)
