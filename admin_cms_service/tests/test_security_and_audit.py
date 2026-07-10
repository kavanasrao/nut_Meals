"""Unit tests for app.core.security (JWT verification, RBAC) and app.core.audit."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.core.audit import record_audit_event
from app.core.security import AdminPrincipal, _decode_token, require_roles
from app.models.audit import AuditLogEntry
from app.models.common import AdminRole

settings = get_settings()


def _build_token(roles: list[str], expired: bool = False) -> str:
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "test@nutmeals.test",
        "roles": roles,
        "aud": settings.jwt_audience,
        "exp": datetime.now(timezone.utc) + (timedelta(hours=-1) if expired else timedelta(hours=1)),
    }
    return jwt.encode(payload, settings.jwt_public_key, algorithm=settings.jwt_algorithm)


def test_decode_valid_token():
    token = _build_token(["content_admin"])
    payload = _decode_token(token)
    assert payload["email"] == "test@nutmeals.test"


def test_decode_expired_token_raises_401():
    token = _build_token(["content_admin"], expired=True)
    with pytest.raises(HTTPException) as exc_info:
        _decode_token(token)
    assert exc_info.value.status_code == 401


def test_decode_garbage_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        _decode_token("not-a-real-jwt")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_roles_super_admin_bypasses_check():
    checker = require_roles(AdminRole.FINANCE_ADMIN)
    admin = AdminPrincipal(admin_id=uuid.uuid4(), email="x@y.com", roles=[AdminRole.SUPER_ADMIN])
    result = await checker(admin=admin)
    assert result == admin


@pytest.mark.asyncio
async def test_require_roles_denies_wrong_role():
    checker = require_roles(AdminRole.FINANCE_ADMIN)
    admin = AdminPrincipal(admin_id=uuid.uuid4(), email="x@y.com", roles=[AdminRole.CONTENT_ADMIN])
    with pytest.raises(HTTPException) as exc_info:
        await checker(admin=admin)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_roles_allows_matching_role():
    checker = require_roles(AdminRole.FINANCE_ADMIN, AdminRole.SUPPORT_ADMIN)
    admin = AdminPrincipal(admin_id=uuid.uuid4(), email="x@y.com", roles=[AdminRole.SUPPORT_ADMIN])
    result = await checker(admin=admin)
    assert result == admin


@pytest.mark.asyncio
async def test_record_audit_event_persists_entry(db_session):
    admin = AdminPrincipal(admin_id=uuid.uuid4(), email="a@b.com", roles=[AdminRole.SUPER_ADMIN])
    entry = await record_audit_event(
        db_session,
        actor=admin,
        action="content.publish",
        resource_type="content_item",
        resource_id=str(uuid.uuid4()),
        metadata={"note": "test"},
    )
    assert isinstance(entry, AuditLogEntry)
    assert entry.action == "content.publish"
    assert entry.actor_admin_id == admin.admin_id
