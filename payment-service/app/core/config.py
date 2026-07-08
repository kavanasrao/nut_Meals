"""Payment Service configuration."""
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

    SERVICE_NAME: str = "payment-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutmeals_payments"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    # ── Provider selection ───────────────────────────────────────────────
    # Set to "juspay", "stripe", or "razorpay"
    PAYMENT_PROVIDER: str = "juspay"

    # ── Juspay credentials ───────────────────────────────────────────────
    JUSPAY_API_KEY: str = ""
    JUSPAY_MERCHANT_ID: str = ""
    JUSPAY_BASE_URL: str = "https://sandbox.juspay.in"
    JUSPAY_WEBHOOK_SECRET: str = ""

    # ── Stripe credentials (placeholder) ────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── Razorpay credentials (placeholder) ──────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
