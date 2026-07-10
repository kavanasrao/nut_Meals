"""Unit tests for RbacService + integration tests for the /rbac API and permission enforcement."""
import pytest

from app.schemas.rbac import PermissionCreate, RoleCreate
from app.services.rbac_service import RbacService
from tests.conftest import auth_headers


@pytest.mark.asyncio
class TestRbacService:
    async def test_create_permission_and_role(self, db_session):
        service = RbacService(db_session)
        perm = await service.create_permission(
            PermissionCreate(code="orders:refund", service="orders", description="Issue refunds")
        )
        assert perm.code == "orders:refund"

        role = await service.create_role(
            RoleCreate(name="finance-lead", description="Finance team lead", permission_codes=["orders:refund"])
        )
        assert role.name == "finance-lead"
        assert any(p.code == "orders:refund" for p in role.permissions)

    async def test_bind_user_role_and_check_access(self, db_session):
        service = RbacService(db_session)
        await service.create_permission(PermissionCreate(code="inventory:adjust", service="inventory"))
        await service.create_role(
            RoleCreate(name="logistics", permission_codes=["inventory:adjust"])
        )
        binding = await service.bind_user_role("user-42", "logistics", granted_by="admin-1")
        assert binding.user_id == "user-42"

        from app.api.deps import user_has_permission

        allowed = await user_has_permission(db_session, "user-42", "inventory:adjust")
        assert allowed is True

        not_allowed = await user_has_permission(db_session, "user-42", "orders:refund")
        assert not_allowed is False

    async def test_bind_user_role_raises_for_unknown_role(self, db_session):
        service = RbacService(db_session)
        with pytest.raises(ValueError):
            await service.bind_user_role("user-1", "nonexistent-role", granted_by="admin-1")

    async def test_revoke_binding_removes_access(self, db_session):
        service = RbacService(db_session)
        await service.create_permission(PermissionCreate(code="support:view_tickets", service="support"))
        await service.create_role(RoleCreate(name="support-agent", permission_codes=["support:view_tickets"]))
        binding = await service.bind_user_role("agent-1", "support-agent", granted_by="admin-1")

        removed = await service.revoke_binding(binding.id)
        assert removed is True

        from app.api.deps import user_has_permission

        allowed = await user_has_permission(db_session, "agent-1", "support:view_tickets")
        assert allowed is False

    async def test_set_role_permissions_replaces_set(self, db_session):
        service = RbacService(db_session)
        await service.create_permission(PermissionCreate(code="a:one", service="a"))
        await service.create_permission(PermissionCreate(code="a:two", service="a"))
        role = await service.create_role(RoleCreate(name="role-x", permission_codes=["a:one"]))

        updated = await service.set_role_permissions(role.id, ["a:two"])
        codes = {p.code for p in updated.permissions}
        assert codes == {"a:two"}


@pytest.mark.asyncio
class TestRbacApi:
    async def test_create_role_requires_permission(self, client, db_session):
        resp = await client.post(
            "/rbac/roles",
            json={"name": "new-role", "permission_codes": []},
            headers=auth_headers(user_id="no-permissions-user"),
        )
        assert resp.status_code == 403

    async def test_full_role_binding_flow(self, client, db_session, admin_user):
        role_resp = await client.post(
            "/rbac/roles",
            json={"name": "api-test-role", "permission_codes": []},
            headers=auth_headers(user_id=admin_user),
        )
        assert role_resp.status_code == 200

        bind_resp = await client.post(
            "/rbac/bindings",
            json={"user_id": "target-user", "role_name": "api-test-role"},
            headers=auth_headers(user_id=admin_user),
        )
        assert bind_resp.status_code == 201

        list_resp = await client.get(
            "/rbac/bindings/target-user", headers=auth_headers(user_id=admin_user)
        )
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

    async def test_access_check_endpoint(self, client, db_session, admin_user):
        check_resp = await client.post(
            "/rbac/check",
            json={"user_id": admin_user, "permission_code": "rbac:manage"},
        )
        assert check_resp.status_code == 200
        assert check_resp.json()["allowed"] is True

        check_resp_denied = await client.post(
            "/rbac/check",
            json={"user_id": "random-unknown-user", "permission_code": "rbac:manage"},
        )
        assert check_resp_denied.json()["allowed"] is False
