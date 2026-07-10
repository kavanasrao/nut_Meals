"""
Centralized configuration. In production, secret values are placeholders
that get resolved from OCI Vault at container startup (see core/security.py
`load_secrets_from_vault`) and injected as env vars before the app boots.
Never commit real secrets — this file only defines *where* to find them.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    service_name: str = "notification-messaging-service"

    database_url: str = "postgresql+asyncpg://notify:notify@localhost:5433/notification_service"
    sync_database_url: str = "postgresql+psycopg2://notify:notify@localhost:5433/notification_service"

    redis_url: str = "redis://localhost:6380/0"
    celery_broker_url: str = "redis://localhost:6380/1"
    celery_result_backend: str = "redis://localhost:6380/2"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    oci_vault_id: str = ""
    oci_vault_secret_smtp: str = ""
    oci_vault_secret_twilio: str = ""
    oci_vault_secret_whatsapp: str = ""

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "notifications@nutmeals.com"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    whatsapp_api_url: str = "https://graph.facebook.com/v19.0"
    whatsapp_token: str = ""
    whatsapp_phone_id: str = ""

    force_https: bool = True

    # Retry policy defaults (overridable per-channel in DB-backed RetryPolicy)
    default_max_retries: int = 5
    default_base_backoff_seconds: int = 30
    default_max_backoff_seconds: int = 3600

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> "Settings":
    return Settings()
