"""Centralised application settings loaded from environment / OCI Vault."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "nut_meals-customer-commerce"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ALLOWED_HOSTS: List[str] = ["*"]

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/customer_commerce"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    JWT_SECRET_KEY: str = "changeme-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    FINANCE_SERVICE_URL: str = "http://finance-service:8001"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8002"

    OCI_BUCKET_NAME: str = "nut-meals-invoices"
    OCI_NAMESPACE: str = ""
    OCI_REGION: str = "ap-mumbai-1"

    COMPANY_NAME: str = "Nut Meals Pvt. Ltd."
    COMPANY_GSTIN: str = "27AABCU9603R1ZX"
    COMPANY_ADDRESS: str = "123, Food Street, Mumbai, Maharashtra - 400001"

    ABANDONED_CART_HOURS: int = 24
    CART_RECOVERY_CRON_MINUTE: str = "0"
    CART_RECOVERY_CRON_HOUR: str = "*/6"

    INVOICE_PREFIX: str = "NM-INV"
    INVOICE_FY_START_MONTH: int = 4

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
