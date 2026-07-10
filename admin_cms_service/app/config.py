"""
Application configuration for the Admin CMS Service.

Secrets (DB credentials, JWT signing keys, service tokens) are NOT stored
in this file or in environment files checked into source control. In
production they are injected at container start time by the OCI Vault
sidecar/init-container, which populates environment variables consumed
here via pydantic BaseSettings. Locally, a `.env` file (gitignored) is
used for developer convenience only.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ADMIN_CMS_", extra="ignore")

    # Service identity
    service_name: str = "admin-cms-service"
    environment: str = "development"  # development | staging | production
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:username@postgrey:5432/database_name"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Auth / RBAC
    jwt_public_key: str = ""  # fetched from OCI Vault at boot in prod
    jwt_algorithm: str = "RS256"
    jwt_audience: str = "nut-meals-admin"

    # Upstream microservices (internal DNS names in the cluster)
    finance_service_url: str = "http://finance-service:8000"
    orders_service_url: str = "http://orders-service:8000"
    logistics_service_url: str = "http://logistics-service:8000"
    payments_service_url: str = "http://payments-service:8000"
    inventory_service_url: str = "http://inventory-service:8000"

    internal_service_token: str = ""  # shared secret for service-to-service auth, from Vault

    # HTTPS enforcement
    force_https: bool = True

    # Audit logging
    audit_log_retention_days: int = 365

    # OCI Vault
    oci_vault_id: str = ""
    oci_vault_region: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton pattern)."""
    return Settings()
