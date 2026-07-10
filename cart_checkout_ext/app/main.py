"""
Cart/Checkout Extensions Service — FastAPI entrypoint.

Extends the core Cart/Checkout microservice with:
  * Gift orders (gift wrapping, recipient details, delivery scheduling)
  * Recurring meal subscriptions (weekly/monthly, lifecycle management)
  * One-click login checkout (saved addresses/payment methods, short-lived
    checkout tokens)

This service owns its own database/schema and is deployed independently
(own Dockerfile, own CI/CD pipeline) as part of the nut_Meals microservices
architecture.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import gift, one_click, subscription

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: nothing to warm up beyond the lazily-created DB engine.
    yield
    # Shutdown: engine disposal is handled by SQLAlchemy's connection pool GC.


app = FastAPI(
    title="nut_Meals Cart/Checkout Extensions Service",
    description="Gift orders, subscriptions, and one-click login checkout.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    """
    Reject plaintext HTTP in production. In practice the ingress/load
    balancer terminates TLS and forwards X-Forwarded-Proto, so we trust
    that header when present; this is a defense-in-depth check, not the
    primary TLS enforcement point.
    """
    if settings.ENFORCE_HTTPS and settings.ENVIRONMENT == "production":
        forwarded_proto = request.headers.get("x-forwarded-proto", "https")
        if forwarded_proto != "https":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "HTTPS is required."},
            )
    return await call_next(request)


app.include_router(gift.router)
app.include_router(subscription.router)
app.include_router(one_click.router)


@app.get("/health", tags=["ops"])
async def health_check():
    """Liveness/readiness probe target for orchestration (k8s/ECS)."""
    return {"status": "ok", "service": settings.SERVICE_NAME}
