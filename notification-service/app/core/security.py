"""
JWT auth + OCI Vault secret loading.

Secrets (SMTP creds, Twilio creds, WhatsApp token) are NEVER stored in
env files in production. `load_secrets_from_vault` is invoked once at
process startup (see app.main lifespan) and populates `os.environ` from
OCI Vault secret bundles before `Settings` is instantiated downstream.
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload:
    def __init__(self, sub: str, roles: list[str]):
        self.sub = sub
        self.roles = roles


def create_access_token(subject: str, roles: list[str], expires_minutes: int = 60) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "roles": roles, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return TokenPayload(sub=payload.get("sub", ""), roles=payload.get("roles", []))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return decode_token(credentials.credentials)


def load_secrets_from_vault() -> None:
    """
    Resolve SMTP/Twilio/WhatsApp credentials from OCI Vault and inject
    them into process env vars. No-ops gracefully if `oci` SDK / vault
    OCID isn't configured (e.g. local dev using .env directly).
    """
    vault_id = os.getenv("OCI_VAULT_ID")
    if not vault_id:
        return

    try:
        import oci  # noqa: local import — optional dependency at runtime

        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        secrets_client = oci.secrets.SecretsClient(config={}, signer=signer)

        secret_env_map = {
            "OCI_VAULT_SECRET_SMTP": ["SMTP_USER", "SMTP_PASSWORD"],
            "OCI_VAULT_SECRET_TWILIO": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"],
            "OCI_VAULT_SECRET_WHATSAPP": ["WHATSAPP_TOKEN"],
        }
        for secret_ocid_env, target_keys in secret_env_map.items():
            secret_ocid = os.getenv(secret_ocid_env)
            if not secret_ocid:
                continue
            bundle = secrets_client.get_secret_bundle(secret_id=secret_ocid)
            content = bundle.data.secret_bundle_content.content
            import base64
            import json

            decoded = json.loads(base64.b64decode(content))
            for key in target_keys:
                if key in decoded:
                    os.environ[key] = decoded[key]
    except Exception as exc:  # pragma: no cover - defensive, environment-dependent
        import logging

        logging.getLogger(__name__).warning("OCI Vault secret load skipped: %s", exc)
