from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.message import Message


async def record_audit_event(
    db: AsyncSession,
    message: Message,
    action: str,
    status: str,
    detail: dict[str, Any] | None = None,
    actor: str = "system",
) -> AuditLog:
    log = AuditLog(
        message_id=message.id,
        actor=actor,
        action=action,
        channel=message.channel.value if message.channel else None,
        recipient=message.recipient,
        detail=detail or {},
        status=status,
    )
    db.add(log)
    await db.commit()
    return log
