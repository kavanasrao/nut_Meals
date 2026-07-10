"""
Application configuration for the Cart/Checkout Extensions service.

All secrets (DB creds, JWT signing key, payment service tokens) are expected
to be injected as environment variables at runtime. In production these are
sourced from OCI Vault via the platform's secret-injection sidecar / init
container — this service never reads Vault directly, it only reads env vars
that the deployment pipeline populates from Vault at container start.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Service identity
    SERVICE_NAME: str = "cart-checkout-extensions"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cart_checkout_ext"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/cart_checkout_ext"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Auth / RBAC
    JWT_SECRET_KEY: str = "changeme-in-vault"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ONE_CLICK_TOKEN_EXPIRE_MINUTES: int = 15

    # Upstream microservices (internal DNS names in the cluster)
    PAYMENTS_SERVICE_URL: str = "http://payments-service.internal:8000"
    NOTIFICATIONS_SERVICE_URL: str = "http://notifications-service.internal:8000"
    CUSTOMER_PROFILE_SERVICE_URL: str = "http://customer-profile-service.internal:8000"

    # Security
    ENFORCE_HTTPS: bool = True
    CORS_ORIGINS: list[str] = ["https://www.nutmeals.com"]

    # Subscription renewal window (days before renewal to notify)
    RENEWAL_NOTICE_DAYS: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
