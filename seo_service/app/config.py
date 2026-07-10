"""
Centralized configuration for the SEO service.

Secrets (DB creds, Redis URL, Vault token, signing keys) are never
hardcoded. In production they are injected as environment variables by
the deployment pipeline, which itself pulls them from OCI Vault at
container start (see `docker-entrypoint.sh` / k8s init container).
Locally, a `.env` file (git-ignored) is used via pydantic-settings.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SEO_", extra="ignore")

    # Service identity
    SERVICE_NAME: str = "seo-service"
    ENV: str = Field(default="development")
    HTTPS_ONLY: bool = Field(default=True)

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://seo_user:seo_pass@localhost:5432/seo_service_db"
    )
    SQL_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis / Celery
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/2")

    # Upstream services (internal cluster DNS in prod)
    CATALOG_SERVICE_URL: str = Field(default="http://catalog-service:8000")
    REVIEWS_SERVICE_URL: str = Field(default="http://reviews-service:8000")
    BLOG_SERVICE_URL: str = Field(default="http://blog-service:8000")
    CATALOG_SERVICE_TIMEOUT_SECONDS: float = 5.0

    # Public-facing
    PUBLIC_BASE_URL: str = Field(default="https://www.nutmeals.com")
    SITEMAP_MAX_URLS_PER_FILE: int = 45000  # Google hard limit is 50,000

    # Auth / RBAC
    JWT_PUBLIC_KEY: str = Field(default="")  # fetched from OCI Vault at boot
    JWT_ALGORITHM: str = "RS256"
    OCI_VAULT_SECRET_ID: str = Field(default="")

    # AI discovery
    AI_EXPORT_PAGE_SIZE: int = 500
    AI_EXPORT_SIGNING_SECRET: str = Field(default="")  # from Vault

    # Observability
    AUDIT_LOG_RETENTION_DAYS: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()
