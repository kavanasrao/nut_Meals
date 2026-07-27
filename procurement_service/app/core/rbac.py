"""
Role-based access control.

Roles used by the Procurement service:
  - procurement_admin : full CRUD, can approve POs, manage vendors
  - procurement_officer: create POs/GRNs/invoices, cannot approve own POs
  - finance_viewer     : read-only access to ledger/invoices
  - auditor            : read-only access to everything
"""
from fastapi import Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user

ROLE_ADMIN = "procurement_admin"
ROLE_OFFICER = "procurement_officer"
ROLE_FINANCE_VIEWER = "finance_viewer"
ROLE_AUDITOR = "auditor"

READ_ROLES = {ROLE_ADMIN, ROLE_OFFICER, ROLE_FINANCE_VIEWER, ROLE_AUDITOR}
WRITE_ROLES = {ROLE_ADMIN, ROLE_OFFICER}
APPROVE_ROLES = {ROLE_ADMIN}


def require_roles(*allowed_roles: str):
    """Dependency factory: raises 403 unless the caller has one of allowed_roles."""

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not user.has_role(*allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _checker


require_read = require_roles(*READ_ROLES)
require_write = require_roles(*WRITE_ROLES)
require_approver = require_roles(*APPROVE_ROLES)
