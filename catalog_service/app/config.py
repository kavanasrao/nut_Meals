"""
Application configuration.

Secrets (DB credentials, JWT signing keys, OCI Vault references) are NEVER
hardcoded. In production they are injected as environment variables by the
deployment pipeline, which itself pulls them from OCI Vault at deploy time
(see .github/workflows/catalog-ci-cd.yml and README "Secrets Management").
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CATALOG_", extra="ignore")

    # Service
    service_name: str = "catalog-service"
    environment: str = Field(default="local")  # local | staging | production
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:username@postgrey:5432/database_name"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis / Celery
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # Auth / RBAC
    jwt_secret_key: str = Field(default="CHANGE_ME_INJECTED_FROM_OCI_VAULT")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Inventory service (internal microservice-to-microservice call)
    inventory_service_url: str = Field(default="http://inventory-service:8000")
    inventory_service_timeout_seconds: float = 3.0

    # Security
    force_https: bool = True
    allowed_origins: List[str] = ["https://www.nutmeals.com"]

    # OCI Vault (referenced, actual secret fetch is done by infra/init container)
    oci_vault_ocid: str = Field(default="")
    oci_vault_secret_prefix: str = Field(default="catalog-service/")

    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
