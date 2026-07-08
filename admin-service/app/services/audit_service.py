"""Audit Log service — persists admin actions to the audit_logs table.

Called by every route that mutates state. Uses the admin's JWT claims
so no extra DB lookup is needed per write.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        admin_id: str,
        admin_email: str,
        admin_role: str,
        action: str,
        resource: str,
        resource_id: str | None = None,
        http_method: str | None = None,
        http_path: str | None = None,
        ip_address: str | None = None,
        request_payload: dict[str, Any] | None = None,
        response_status: int | None = None,
    ) -> None:
        """
        Append an immutable audit entry.
        This is fire-and-forget — a failure here should NOT roll back the main action.
        """
        import uuid

        entry = AuditLog(
            id=uuid.uuid4(),
            admin_id=admin_id,
            admin_email=admin_email,
            admin_role=admin_role,
            action=action,
            resource=resource,
            resource_id=resource_id,
            http_method=http_method,
            http_path=http_path,
            ip_address=ip_address,
            request_payload=request_payload,
            response_status=response_status,
        )
        self.db.add(entry)
        try:
            await self.db.commit()
        except Exception as exc:
            logger.error("Failed to persist audit log: %s", exc)
            await self.db.rollback()
