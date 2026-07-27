"""
Application configuration.
All secrets are loaded from environment variables. In production these
env vars are injected by the deployment platform after being pulled from
OCI Vault (see docs/DEPLOYMENT.md) — never hardcode secrets here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Service
    SERVICE_NAME: str = "procurement-service"
    ENV: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://procurement:procurement@localhost:5432/procurement_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Auth / RBAC
    JWT_SECRET_KEY: str = "changeme-in-vault"
    JWT_ALGORITHM: str = "HS256"
    JWT_AUDIENCE: str = "nut-meals"

    # Downstream services
    FINANCE_SERVICE_BASE_URL: str = "http://finance-service:8000"
    FINANCE_SERVICE_API_KEY: str = "changeme-in-vault"

    # OCI Vault
    OCI_VAULT_ID: str = ""
    OCI_VAULT_COMPARTMENT_ID: str = ""

    # Misc
    PO_REMINDER_DAYS_BEFORE_DUE: int = 2
    INVOICE_RECONCILIATION_INTERVAL_MINUTES: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
