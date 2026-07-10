import pytest
from fastapi import HTTPException

from app.core.security import create_access_token, decode_token


def test_create_and_decode_token_roundtrip():
    token = create_access_token(subject="svc-order", roles=["notifier"])
    payload = decode_token(token)
    assert payload.sub == "svc-order"
    assert payload.roles == ["notifier"]


def test_decode_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-real-token")
    assert exc_info.value.status_code == 401


def test_load_secrets_from_vault_noop_without_vault_id(monkeypatch):
    from app.core.security import load_secrets_from_vault

    monkeypatch.delenv("OCI_VAULT_ID", raising=False)
    # Should not raise even though no vault is configured
    load_secrets_from_vault()
