"""Delivery Service configuration."""
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

    SERVICE_NAME: str = "delivery-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutmeals_delivery"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    # Redis TTL for cached delivery options (seconds)
    DELIVERY_OPTIONS_CACHE_TTL: int = 300  # 5 minutes

    # Delivery rules
    HOME_DELIVERY_RADIUS_KM: float = 15.0
    HOME_DELIVERY_BASE_ETA_MINUTES: int = 40
    PICKUP_BASE_ETA_MINUTES: int = 10

    # Operating hours (24h format)
    SERVICE_START_HOUR: int = 8   # 08:00
    SERVICE_END_HOUR: int = 22    # 22:00

    # Restaurant location (used for ETA calculation)
    RESTAURANT_LAT: float = 13.0827
    RESTAURANT_LON: float = 80.2707


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
