"""Send backup/restore notifications to Slack or email."""

import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def notify_backup_success(db_alias: str, job_id: str, size_bytes: int, s3_key: str) -> None:
    mb = size_bytes / 1024 / 1024
    msg = (
        f"✅ *Backup succeeded* — `{db_alias}`\n"
        f"> Job: `{job_id}`\n"
        f"> Size: `{mb:.1f} MB`\n"
        f"> S3 key: `{s3_key}`"
    )
    await _send_slack(msg)


async def notify_backup_failure(db_alias: str, job_id: str, error: str) -> None:
    msg = (
        f"❌ *Backup FAILED* — `{db_alias}`\n"
        f"> Job: `{job_id}`\n"
        f"> Error: ```{error[:300]}```"
    )
    await _send_slack(msg)


async def notify_restore_complete(backup_job_id: str, target_alias: str) -> None:
    msg = (
        f"🔄 *Restore complete* — target: `{target_alias}`\n"
        f"> Backup job: `{backup_job_id}`"
    )
    await _send_slack(msg)


async def _send_slack(text: str) -> None:
    if not settings.SLACK_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.SLACK_WEBHOOK_URL, json={"text": text})
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Slack notification failed", error=str(exc))
