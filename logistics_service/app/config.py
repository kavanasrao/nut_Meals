"""
Central configuration for the Logistics Service.

All secrets (API keys, DB creds) are expected to be injected as environment
variables. In production these are sourced from OCI Vault via the deployment
pipeline / init-container and never committed to source control.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LOGISTICS_")

    service_name: str = "logistics-service"
    environment: str = "development"

    # Database
    DATABASE_URL: str = (
    "postgresql+asyncpg://postgres:kanni3750@localhost:5432/nutmeals_db"
)
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Serviceability cache TTL (seconds)
    serviceability_cache_ttl: int = 3600

    # Carrier credentials (pulled from OCI Vault -> env at deploy time)
    delhivery_api_base: str = "https://track.delhivery.com"
    delhivery_api_token: str = ""
    india_post_api_base: str = "https://api.indiapost.gov.in"
    india_post_api_key: str = ""

    # Internal service URLs
    orders_service_url: str = "http://orders-service:8000"
    inventory_service_url: str = "http://inventory-service:8000"
    messaging_service_url: str = "http://messaging-service:8000"

    # Security
    jwt_public_key: str = ""
    jwt_algorithm: str = "RS256"
    enforce_https: bool = True

    # Carrier selection rules engine weights
    weight_cost: float = 0.4
    weight_speed: float = 0.4
    weight_reliability: float = 0.2


@lru_cache
def get_settings() -> Settings:
    return Settings()
