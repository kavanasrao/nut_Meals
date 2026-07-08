"""Admin Service — centralised configuration."""
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

    SERVICE_NAME: str = "admin-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    # ── Database (admin-service owns its own DB) ─────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutmeals_admin"

    # ── Redis (optional caching) ─────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ──────────────────────────────────────────────────────────────
    JWT_SECRET: str = "change_me_admin_secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Downstream service base URLs ─────────────────────────────────────
    USER_SERVICE_URL: str = "http://user-service:8005"
    ORDER_SERVICE_URL: str = "http://order-service:8001"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8002"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8003"
    DELIVERY_SERVICE_URL: str = "http://delivery-service:8004"
    MEAL_SERVICE_URL: str = "http://meal-service:8006"

    # Internal token for service-to-service calls
    INTERNAL_SERVICE_TOKEN: str = "change_me_internal"

    # HTTP client timeout (seconds) for downstream calls
    DOWNSTREAM_TIMEOUT: float = 15.0


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
