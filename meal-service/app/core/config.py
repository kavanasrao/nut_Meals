"""Meal Service configuration."""
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

    SERVICE_NAME: str = "meal-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:username@postgrey:5432/database_name"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    INTERNAL_SERVICE_TOKEN: str = "change_me_internal"

    # Redis TTL for meal list cache (seconds)
    MEAL_CACHE_TTL: int = 600   # 10 minutes
    MEAL_CACHE_KEY: str = "meals:list"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
