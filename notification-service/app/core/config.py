"""Notification Service configuration."""
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

    SERVICE_NAME: str = "notification-service"
    ENVIRONMENT: str = "local"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/nutmeals_notifications"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── WhatsApp provider selection ──────────────────────────────────────
    # Options: "twilio" | "meta"
    WHATSAPP_PROVIDER: str = "twilio"

    # ── Twilio credentials ───────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"  # Twilio sandbox number

    # ── Meta / WhatsApp Business API credentials ─────────────────────────
    META_WHATSAPP_ACCESS_TOKEN: str = ""
    META_WHATSAPP_PHONE_NUMBER_ID: str = ""

    # ── Retry policy ─────────────────────────────────────────────────────
    # Comma-separated seconds to wait before each retry attempt
    NOTIFICATION_RETRY_DELAYS: str = "30,120,600"
    NOTIFICATION_MAX_RETRIES: int = 3

    # ── Redis channels to subscribe (comma-separated EventType values) ───
    SUBSCRIBED_CHANNELS: str = "ORDER_CREATED,PAYMENT_SUCCESS,DELIVERY_ASSIGNED"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
