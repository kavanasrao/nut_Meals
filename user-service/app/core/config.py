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

    # ── Celery (background tasks: OTP delivery, password reset emails) ─────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Forgot / Reset password ─────────────────────────────────────────────────
    PASSWORD_RESET_TOKEN_TTL_MINUTES: int = 30
    PASSWORD_RESET_BASE_URL: str = "https://app.nutmeals.com/reset-password"

    # ── OTP login ────────────────────────────────────────────────────────────────
    OTP_LENGTH: int = 6
    OTP_TTL_SECONDS: int = 300  # 5 minutes
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    # ── Google OAuth / Social Login ─────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = "change_me_google_client_id.apps.googleusercontent.com"
    GOOGLE_TOKENINFO_URL: str = "https://oauth2.googleapis.com/tokeninfo"

    # ── Downstream service integrations (internal, service-to-service) ─────────
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8003"
    ORDER_SERVICE_URL: str = "http://order-service:8001"
    CRM_SERVICE_URL: str = "http://crm-service:8000"
    SERVICE_HTTP_TIMEOUT_SECONDS: float = 5.0

    # ── Security ─────────────────────────────────────────────────────────────────
    ENFORCE_HTTPS: bool = False
    OCI_VAULT_ENABLED: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
