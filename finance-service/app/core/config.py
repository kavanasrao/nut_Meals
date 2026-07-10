"""
Application configuration.

Secrets (DB credentials, Redis URL, JWT signing keys, payment gateway API keys)
are NOT hardcoded. In production they are injected as environment variables
by the deployment pipeline, which itself pulls them from OCI Vault at deploy
time (see ops/vault_bootstrap.sh in the platform repo). Locally, a .env file
(never committed - see .gitignore) is used via python-dotenv/pydantic-settings.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FINANCE_", extra="ignore")

    # --- Service identity ---
    SERVICE_NAME: str = "finance-service"
    ENV: str = Field(default="local")  # local | staging | production
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://finance:finance@localhost:5432/finance_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://finance:finance@localhost:5432/finance_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- Security ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_VAULT"  # overridden via env/OCI Vault injection
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "nut-meals-auth"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    FORCE_HTTPS: bool = True
    ALLOWED_ORIGINS: list[str] = ["https://admin.nutmeals.com"]

    # --- OCI Vault (referenced, not called directly here; secrets are
    # resolved by the platform's init-container / external-secrets operator
    # and mounted as env vars before the container starts) ---
    OCI_VAULT_SECRET_OCID: str = ""
    OCI_VAULT_COMPARTMENT_ID: str = ""

    # --- Reconciliation ---
    RECONCILIATION_AMOUNT_TOLERANCE_PAISE: int = 100  # allow 1 rupee mismatch before flagging
    JUSPAY_API_BASE: str = "https://api.juspay.in"
    KOTAK_SETTLEMENT_SFTP_HOST: str = ""

    # --- Currency ---
    BASE_CURRENCY: str = "INR"


@lru_cache
def get_settings() -> Settings:
    return Settings()
