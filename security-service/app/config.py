"""
Application configuration for the Security Service.

Settings are loaded from environment variables (12-factor style). In production,
secrets (DB creds, JWT signing keys, Vault tokens) are injected via OCI Vault ->
env vars at container start, never committed to source control.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central settings object for the security-service."""

    # --- Service identity ---
    SERVICE_NAME: str = "security-service"
    ENV: str = Field(default="local", description="local | staging | production")

    # --- Database ---
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://nutmeals:nutmeals@security-db:5432/security_db",
        description="Async SQLAlchemy DSN for Postgres",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Redis / Celery ---
    REDIS_URL: str = Field(default="redis://security-redis:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://security-redis:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://security-redis:6379/2")

    # --- Auth / RBAC ---
    JWT_SECRET: str = Field(default="change-me-in-vault", description="Fetched from OCI Vault in prod")
    JWT_ALGORITHM: str = "HS256"
    AUTH_SERVICE_URL: str = Field(default="http://auth-service:8000")

    # --- WAF ---
    WAF_ENABLED: bool = True
    WAF_BLOCK_MODE: bool = True  # False = log-only/monitor mode
    WAF_MAX_BODY_BYTES: int = 1_000_000

    # --- Compliance ---
    COMPLIANCE_EXPORT_BUCKET: str = Field(default="oci://nutmeals-compliance-exports")

    # --- CORS / security headers ---
    ALLOWED_ORIGINS: List[str] = ["https://admin.nutmeals.com"]
    ENFORCE_HTTPS: bool = True

    # --- Vault ---
    OCI_VAULT_SECRET_OCID: str = Field(default="")
    OCI_VAULT_ENABLED: bool = False

    class Config:
        env_file = ".env"
        env_prefix = "SECURITY_"


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so we don't re-parse env vars on every call."""
    return Settings()
