"""Catalog Service - FastAPI application entrypoint.

Handles product catalog management, SEO metadata, customer reviews, and the
URL redirect manager, as an independently deployable microservice.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.logging_config import configure_logging
from app.core.security import HTTPSEnforcementMiddleware
from app.routers import health, products, redirects, reviews, seo

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.debug)
    yield


app = FastAPI(
    title="nut_Meals Catalog Service",
    description="Product catalog, SEO metadata, reviews, and redirect management.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(HTTPSEnforcementMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health.router)
app.include_router(products.router)
app.include_router(seo.router)
app.include_router(reviews.router)
app.include_router(redirects.router)
