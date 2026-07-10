"""
Application configuration.

Secrets (DB credentials, Redis URL, JWT signing keys) are NOT stored in this
repo. In production they are injected as environment variables sourced from
OCI Vault via the deployment pipeline (see .github/workflows/inventory-ci.yml
and the `oci vault secret get` step documented in README.md).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Service identity
    SERVICE_NAME: str = "inventory-service"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = (
    "postgresql+asyncpg://postgres:kanni3750@localhost:5432/nutmeals_db"
)
    
    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Reservation behavior
    RESERVATION_TTL_SECONDS: int = 900  # 15 minutes before auto-release

    # Security
    JWT_SECRET_KEY: str = "changeme-in-vault"
    JWT_ALGORITHM: str = "HS256"
    FORCE_HTTPS: bool = True

    # Orders service integration
    ORDERS_SERVICE_BASE_URL: str = "http://orders-service:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
