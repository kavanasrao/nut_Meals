"""
Manufacturing Service configuration — reads from environment variables / .env file.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    SERVICE_NAME: str = "manufacturing-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"

    HOST: str = "0.0.0.0"
    PORT: int = 8010

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/"
        "nutmeals_manufacturing"
    )

    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"

    REDIS_CACHE_TTL: int = 3600

    # ------------------------------------------------------------------
    # Celery
    # ------------------------------------------------------------------
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    # ------------------------------------------------------------------
    # Internal Service Communication
    # ------------------------------------------------------------------
    INTERNAL_SERVICE_TOKEN: str = "change_me_internal"

    PRODUCT_SERVICE_URL: str = "http://product-service:8003"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8004"
    FINANCE_SERVICE_URL: str = "http://finance-service:8007"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8008"
    ORDER_SERVICE_URL: str = "http://order-service:8005"

    # ------------------------------------------------------------------
    # Manufacturing
    # ------------------------------------------------------------------
    DEFAULT_BOM_VERSION: int = 1

    LOW_STOCK_THRESHOLD_PERCENT: int = 20

    BATCH_NUMBER_PREFIX: str = "BAT"

    LOT_NUMBER_PREFIX: str = "LOT"

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    LOG_FORMAT: str = (
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()