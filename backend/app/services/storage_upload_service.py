"""
Storage Upload Service — handles file validation, secure server-side upload
via Supabase Storage service-role client, and compensating cleanup.
"""

import logging
import uuid
from typing import Optional, Set

from fastapi import UploadFile

from app.config.settings import get_settings
from app.db.storage import get_storage_client
from app.utils.exceptions import BadRequestError, DatabaseError

logger = logging.getLogger(__name__)

# Constants
NOTICES_BUCKET = "official-updates"
NOTICES_ALLOWED_EXTENSIONS: Set[str] = {
    "pdf", "jpg", "jpeg", "png", "gif", "webp",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx",
}
NOTICES_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

PAPERS_BUCKET = "papers"
PAPERS_ALLOWED_EXTENSIONS: Set[str] = {"pdf"}
PAPERS_MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

NEWS_BUCKET = "news-media"
NEWS_ALLOWED_EXTENSIONS: Set[str] = {"jpg", "jpeg", "png", "webp", "gif", "svg", "pdf"}
NEWS_MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB

# MIME type mapping for preview / file-type detection
FILE_TYPE_MAP: dict[str, str] = {
    "pdf": "pdf",
    "jpg": "image", "jpeg": "image", "png": "image", "gif": "image", "webp": "image", "svg": "image",
    "doc": "docx", "docx": "docx",
    "xls": "xlsx", "xlsx": "xlsx",
    "ppt": "pptx", "pptx": "pptx",
}


async def validate_and_upload_file(
    file: UploadFile,
    bucket: str,
    allowed_extensions: Set[str],
    max_size_bytes: int,
) -> tuple[str, str, str]:
    """
    Validate and upload an UploadFile to Supabase Storage using the service-role client.

    Returns:
        tuple[storage_path, public_url, file_type]
    """
    original_name = file.filename or "file"
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

    if not ext or ext not in allowed_extensions:
        raise BadRequestError(
            f"Unsupported file format '.{ext}'. Allowed formats: {', '.join(sorted(allowed_extensions))}."
        )

    contents = await file.read()
    if not contents or len(contents) == 0:
        raise BadRequestError("Uploaded file is empty.")

    if len(contents) > max_size_bytes:
        max_mb = max_size_bytes // (1024 * 1024)
        raise BadRequestError(f"File size exceeds the maximum allowed limit of {max_mb} MB.")

    storage_path = f"{uuid.uuid4()}.{ext}"
    content_type = file.content_type or "application/octet-stream"
    file_type = FILE_TYPE_MAP.get(ext, "other")

    storage = get_storage_client()
    try:
        storage.from_(bucket).upload(
            path=storage_path,
            file=contents,
            file_options={"content-type": content_type, "upsert": "false"},
        )
    except Exception as exc:
        logger.error(
            "Supabase Storage upload failed for bucket=%s path=%s: %s",
            bucket,
            storage_path,
            exc,
        )
        raise DatabaseError(f"Failed to upload file to storage: {exc}") from exc

    # Resolve public CDN URL
    try:
        url_res = storage.from_(bucket).get_public_url(storage_path)
        if isinstance(url_res, str):
            public_url = url_res
        elif isinstance(url_res, dict):
            public_url = url_res.get("publicUrl") or url_res.get("publicURL")
        else:
            public_url = None
    except Exception:
        public_url = None

    if not public_url:
        settings = get_settings()
        base = settings.SUPABASE_URL.rstrip("/") if settings.SUPABASE_URL else ""
        public_url = f"{base}/storage/v1/object/public/{bucket}/{storage_path}"

    return storage_path, public_url, file_type


def cleanup_storage_file(bucket: str, storage_path: str) -> None:
    """
    Compensating cleanup: Safely delete an uploaded file from Supabase Storage
    if the subsequent database transaction fails.
    """
    if not bucket or not storage_path:
        return
    try:
        storage = get_storage_client()
        storage.from_(bucket).remove([storage_path])
        logger.info(
            "Compensating cleanup: removed file %s from bucket %s",
            storage_path,
            bucket,
        )
    except Exception as exc:
        logger.warning(
            "Compensating cleanup failed for file %s in bucket %s: %s",
            storage_path,
            bucket,
            exc,
        )

