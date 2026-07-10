"""Central configuration — all values sourced from environment variables."""

from functools import lru_cache
from typing import List, Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Application ──────────────────────────────────────────────────────────
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"           # development | staging | production
    DEBUG: bool = False
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = []
    INTERNAL_API_KEY: str                      # service-to-service auth header

    # ── PostgreSQL (infra service own DB) ────────────────────────────────────
    DATABASE_URL: str                          # asyncpg DSN
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/3"

    # ── Celery ───────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://redis:6379/3"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/3"

    # ── Backup — PostgreSQL targets ──────────────────────────────────────────
    # Comma-separated list: alias=DSN, e.g. "orders=postgresql://...,users=postgresql://..."
    BACKUP_DB_TARGETS: str = ""

    # ── Object Storage (S3-compatible / OCI Object Storage) ──────────────────
    S3_ENDPOINT_URL: Optional[str] = None      # None = AWS S3; set for OCI / MinIO
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "nut-meals-backups"
    S3_REGION: str = "us-east-1"
    S3_PATH_PREFIX: str = "backups"

    # ── Backup Encryption ────────────────────────────────────────────────────
    BACKUP_ENCRYPTION_KEY: str                 # 32-byte base64 Fernet key
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_SCHEDULE_CRON: str = "0 2 * * *"   # 02:00 UTC daily

    # ── Docker Registry ──────────────────────────────────────────────────────
    DOCKER_REGISTRY: str = "ghcr.io"
    DOCKER_ORG: str = "nut-meals"
    DOCKER_USERNAME: str = ""
    DOCKER_PASSWORD: str = ""

    # ── Notifications ────────────────────────────────────────────────────────
    SLACK_WEBHOOK_URL: Optional[str] = None
    ALERT_EMAIL: Optional[str] = None

    # ── Validators ───────────────────────────────────────────────────────────
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    def backup_db_targets_parsed(self) -> dict[str, str]:
        """Return {alias: dsn} mapping from BACKUP_DB_TARGETS."""
        if not self.BACKUP_DB_TARGETS:
            return {}
        targets = {}
        for entry in self.BACKUP_DB_TARGETS.split(","):
            entry = entry.strip()
            if "=" in entry:
                alias, dsn = entry.split("=", 1)
                targets[alias.strip()] = dsn.strip()
        return targets


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
