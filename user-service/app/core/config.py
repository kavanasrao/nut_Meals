"""User Service configuration."""
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

    SERVICE_NAME: str = "user-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    # Database (asyncpg driver)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutmeals_users"

    # Redis (caching + optional pub/sub)
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT — shared secret with API Gateway
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Internal token for service-to-service calls
    INTERNAL_SERVICE_TOKEN: str = "change_me_internal"

    # Redis TTL for user profile cache (seconds)
    USER_CACHE_TTL: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
