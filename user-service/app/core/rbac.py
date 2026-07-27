"""Role-based access control dependencies for the User Service.

The User Service owns a simple local role (`UserRole.USER` / `UserRole.ADMIN`)
on the `users` table, which is sufficient for gating admin-only endpoints in
this service. Finer-grained, cross-service permissions (e.g. "audit:export")
are owned by the security-service's RBAC module — see
`app.integrations.security_client` for how this service can defer to it when
an endpoint needs a permission beyond simple admin/user.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import require_active_user
from app.models.user import User, UserRole


def require_role(*roles: UserRole):
    """Dependency factory: only allow users whose role is in `roles`."""

    async def _checker(user: User = Depends(require_active_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return _checker


require_admin = require_role(UserRole.ADMIN)
