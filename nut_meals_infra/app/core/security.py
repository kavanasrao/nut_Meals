"""Security helpers: internal API-key auth and Fernet encryption."""

import base64
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)


async def verify_internal_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """Dependency: enforce service-to-service auth."""
    if not api_key or not secrets.compare_digest(api_key, settings.INTERNAL_API_KEY):
        logger.warning("Unauthorised internal API call")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return api_key


def get_fernet() -> Fernet:
    """Return a Fernet instance from the configured encryption key."""
    key = settings.BACKUP_ENCRYPTION_KEY
    # Accept raw 32-byte key or already-encoded Fernet key
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        # Derive proper key if raw bytes provided
        encoded = base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b"\0"))
        return Fernet(encoded)


def encrypt_bytes(data: bytes) -> bytes:
    return get_fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    return get_fernet().decrypt(token)


def generate_fernet_key() -> str:
    """Generate a new Fernet key (utility, not used at runtime)."""
    return Fernet.generate_key().decode()
