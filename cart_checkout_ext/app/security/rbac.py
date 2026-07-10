"""Role-based access control dependencies for checkout endpoints.

Roles are asserted by the upstream auth service and embedded in the JWT.
This module only enforces them; it does not manage role assignment.
"""
from fastapi import Depends, HTTPException, status

from app.security.audit import log_audit_event
from app.security.auth import Principal, get_current_principal


class RequireRole:
    """
    Dependency factory: `Depends(RequireRole("customer"))` ensures the
    caller has the given role, or is an admin (admins can act on behalf
    of support workflows, e.g. cancelling a subscription for a customer
    who called support).
    """

    def __init__(self, *allowed_roles: str):
        self.allowed_roles = set(allowed_roles) | {"admin"}

    async def __call__(self, principal: Principal = Depends(get_current_principal)) -> Principal:
        if not any(principal.has_role(role) for role in self.allowed_roles):
            log_audit_event(
                actor_id=principal.customer_id,
                action="access_denied",
                resource="rbac",
                detail=f"missing one of roles={self.allowed_roles}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return principal


require_customer = RequireRole("customer")
require_admin = RequireRole("admin")
