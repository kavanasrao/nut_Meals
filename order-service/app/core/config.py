"""Order Service configuration — reads from environment variables / .env file."""
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

    # App
    SERVICE_NAME: str = "order-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    # Database (async driver: asyncpg)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutmeals_orders"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT — shared secret with API Gateway
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    # Internal service token (used when order-service calls other services)
    INTERNAL_SERVICE_TOKEN: str = "change_me_internal"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
