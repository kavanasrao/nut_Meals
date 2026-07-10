"""Global pytest fixtures and configuration."""

import os
import pytest

# Set test environment before any app imports
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("INTERNAL_API_KEY", "dev-internal-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/infra_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/3")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/3")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/3")
os.environ.setdefault("BACKUP_ENCRYPTION_KEY", "aaaabbbbccccddddeeeeffffgggghhhh")
os.environ.setdefault("S3_BUCKET_NAME", "nut-meals-backups-test")
os.environ.setdefault("S3_ACCESS_KEY_ID", "test")
os.environ.setdefault("S3_SECRET_ACCESS_KEY", "test")
os.environ.setdefault("BACKUP_DB_TARGETS", "orders=postgresql://orders:pw@localhost/orders_db")


pytest_plugins = ["pytest_asyncio"]
