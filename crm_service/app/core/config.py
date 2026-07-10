from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "CRM Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    HOST: str = "0.0.0.0"
    PORT: int = 8010

    # Database
    DATABASE_URL: str = Field(...)

    # JWT
    SECRET_KEY: str = Field(...)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Existing Services
    AUTH_SERVICE_URL: str = "http://auth-service:8001"
    USER_SERVICE_URL: str = "http://user-service:8002"
    PRODUCT_SERVICE_URL: str = "http://product-service:8003"
    ORDER_SERVICE_URL: str = "http://order-service:8004"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8005"
    FINANCE_SERVICE_URL: str = "http://finance-service:8006"
    LOGISTICS_SERVICE_URL: str = "http://logistics-service:8007"
    MANUFACTURING_SERVICE_URL: str = "http://manufacturing-service:8008"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8009"
    ADMIN_SERVICE_URL: str = "http://admin-service:8011"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()