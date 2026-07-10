"""Object storage inspection endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import verify_internal_api_key
from app.schemas.backup import StorageStatsResponse
from app.services.storage import generate_presigned_url, get_storage_stats, list_backups

router = APIRouter(dependencies=[Depends(verify_internal_api_key)])


@router.get("/stats", response_model=StorageStatsResponse)
async def storage_stats():
    """Return aggregate statistics for the backup bucket."""
    stats = await get_storage_stats()
    return StorageStatsResponse(**stats)


@router.get("/objects")
async def list_storage_objects(db_alias: str | None = Query(None)):
    """List raw S3 objects, optionally filtered by DB alias."""
    objects = await list_backups(db_alias=db_alias)
    return {"objects": objects, "count": len(objects)}


@router.get("/presign")
async def presigned_download_url(
    s3_key: str = Query(..., description="Full S3 object key"),
    expiry_seconds: int = Query(3600, ge=60, le=86400),
):
    """
    Generate a time-limited pre-signed download URL.

    Note: the downloaded object is Fernet-encrypted; decrypt with
    `scripts/recovery/decrypt_backup.py` before restoring manually.
    """
    try:
        url = await generate_presigned_url(s3_key, expiry_seconds)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return {"url": url, "expires_in_seconds": expiry_seconds}
