"""API Gateway configuration."""
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

    SERVICE_NAME: str = "api-gateway"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    # Redis (used for rate limiting)
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT — must match all downstream services
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    # ── Downstream service base URLs ─────────────────────────────────────
    ORDER_SERVICE_URL: str = "http://order-service:8001"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8002"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8003"
    DELIVERY_SERVICE_URL: str = "http://delivery-service:8004"
    USER_SERVICE_URL: str = "http://user-service:8005"
    MEAL_SERVICE_URL: str = "http://meal-service:8006"

    # ── Rate limiting (requests per window per IP) ───────────────────────
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_MAX_REQUESTS: int = 100       # general endpoints
    RATE_LIMIT_AUTH_MAX_REQUESTS: int = 10   # auth-sensitive endpoints

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: str = "*"

    # Internal service token (for health checks and internal calls)
    INTERNAL_SERVICE_TOKEN: str = "change_me_internal"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
