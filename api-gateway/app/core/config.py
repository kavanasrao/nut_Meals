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

    # JWT — must match all downstream HS256 services (see docker-compose notes:
    # 3 services — logistics, seo, admin-cms — verify with RS256 public keys
    # instead and are NOT compatible with this shared secret. That's a
    # separate, unresolved cross-service auth mismatch — not fixable here.)
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"

    # ── Downstream service base URLs ─────────────────────────────────────
    # NOTE: every one of these must point at the *actual* internal port the
    # target container listens on (see each service's Dockerfile CMD/EXPOSE),
    # not necessarily the host-mapped port. Several services in this repo
    # bind to a different internal port than their docker-compose external
    # mapping implies — see docker-compose.yml comments for the mismatches.
    SECURITY_SERVICE_URL: str = "http://security-service:8000"
    USER_SERVICE_URL: str = "http://user-service:8005"
    CATALOG_SERVICE_URL: str = "http://catalog-service:8000"
    MEAL_SERVICE_URL: str = "http://meal-service:8006"
    CUSTOMER_COMMERCE_SERVICE_URL: str = "http://customer-commerce-service:8000"
    INVENTORY_SERVICE_URL: str = "http://inventory-service:8001"
    ORDER_SERVICE_URL: str = "http://order-service:8001"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8002"
    MANUFACTURING_SERVICE_URL: str = "http://manufacturing-service:8001"
    PROCUREMENT_SERVICE_URL: str = "http://procurement-service:8000"
    LOGISTICS_SERVICE_URL: str = "http://logistics-service:8000"
    CRM_SERVICE_URL: str = "http://crm-service:8005"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8000"
    SEO_SERVICE_URL: str = "http://seo-service:8000"
    FINANCE_SERVICE_URL: str = "http://finance-service:8000"
    ADMIN_SERVICE_URL: str = "http://admin-service:8007"
    ADMIN_CMS_SERVICE_URL: str = "http://admin-cms-service:8000"

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