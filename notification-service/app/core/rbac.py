"""
Role-Based Access Control for messaging/notification/audit endpoints.

Roles:
  - notifier        : can trigger notifications (order/payment/delivery services)
  - messaging_admin  : full read/write on messages, DLQ reprocessing
  - auditor          : read-only access to audit logs & compliance exports
  - support          : read-only access to message status (customer support)
"""
from fastapi import Depends, HTTPException, status

from app.core.security import TokenPayload, get_current_user

ROLE_NOTIFIER = "notifier"
ROLE_MESSAGING_ADMIN = "messaging_admin"
ROLE_AUDITOR = "auditor"
ROLE_SUPPORT = "support"

ALL_ROLES = {ROLE_NOTIFIER, ROLE_MESSAGING_ADMIN, ROLE_AUDITOR, ROLE_SUPPORT}


def require_roles(*allowed_roles: str):
    """Dependency factory: raises 403 unless the caller has one of allowed_roles."""

    async def _check(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if not set(user.roles) & set(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _check


require_notifier = require_roles(ROLE_NOTIFIER, ROLE_MESSAGING_ADMIN)
require_messaging_admin = require_roles(ROLE_MESSAGING_ADMIN)
require_auditor = require_roles(ROLE_AUDITOR, ROLE_MESSAGING_ADMIN)
# Notifier services (order/payment/delivery) are allowed to check the status
# of messages they triggered, in addition to support/auditor/admin roles.
require_read_access = require_roles(ROLE_SUPPORT, ROLE_AUDITOR, ROLE_MESSAGING_ADMIN, ROLE_NOTIFIER)
