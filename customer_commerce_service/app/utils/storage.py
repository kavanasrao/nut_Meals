"""OCI Object Storage upload utility."""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def upload_to_oci(data: bytes, object_name: str) -> str:
    """
    Upload bytes to OCI Object Storage.
    Returns the public URL of the uploaded object.

    In development/test environments, returns a mock URL.
    In production, uses the OCI SDK with instance principal auth.
    """
    if settings.ENVIRONMENT in ("development", "test"):
        logger.info("DEV: skipping OCI upload for %s (%d bytes)", object_name, len(data))
        return f"https://mock-storage.local/{object_name}"

    try:
        import oci  # type: ignore

        config = oci.config.from_file()
        object_storage = oci.object_storage.ObjectStorageClient(config)

        object_storage.put_object(
            namespace_name=settings.OCI_NAMESPACE,
            bucket_name=settings.OCI_BUCKET_NAME,
            object_name=object_name,
            put_object_body=data,
            content_type="application/pdf",
        )

        region = settings.OCI_REGION
        namespace = settings.OCI_NAMESPACE
        bucket = settings.OCI_BUCKET_NAME
        return (
            f"https://objectstorage.{region}.oraclecloud.com/n/{namespace}"
            f"/b/{bucket}/o/{object_name}"
        )
    except Exception as exc:
        logger.exception("OCI upload failed for %s", object_name)
        raise
