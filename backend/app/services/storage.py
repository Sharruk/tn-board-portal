"""
Storage Service
===============
Abstracts file storage so the business logic in admin.py stays unchanged
when swapping providers.

SWAPPING PROVIDERS
------------------
1. Implement the StorageProvider interface below.
2. Register the new class in _PROVIDERS.
3. Set STORAGE_BACKEND=<name> in your .env / Replit Secrets.

Current providers
-----------------
  local     — saves to /uploads/ on the local filesystem (default, dev only)
  s3        — stub for AWS S3 (fill in S3StorageProvider)
  supabase  — Supabase Storage (fully implemented, production-ready)

WARNING: "local" storage is ephemeral on Replit managed VMs.
         Switch to supabase (or s3) before going live.
"""

import os
import uuid
import logging
from abc import ABC, abstractmethod
from fastapi import UploadFile, HTTPException
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, STORAGE_BACKEND

logger = logging.getLogger(__name__)


# ── Interface ─────────────────────────────────────────────────────────────────

class StorageProvider(ABC):
    @abstractmethod
    async def save(self, file: UploadFile) -> tuple[str, str]:
        """
        Persist the file and return (stored_filename, public_url).
        stored_filename is passed back to delete() later.
        public_url is returned to the client and stored in the DB.
        """

    @abstractmethod
    def delete(self, stored_filename: str) -> None:
        """Remove the file identified by stored_filename."""


# ── Local filesystem ──────────────────────────────────────────────────────────

class LocalStorageProvider(StorageProvider):
    """
    Stores files in the /uploads/ directory on the local filesystem.
    Suitable for development. NOT suitable for production on Replit
    (filesystem is reset on each deployment).
    """

    async def save(self, file: UploadFile) -> tuple[str, str]:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB} MB.",
            )
        ext = file.filename.rsplit(".", 1)[-1].lower()
        stored_filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, stored_filename)
        with open(file_path, "wb") as f:
            f.write(content)
        public_url = f"/uploads/{stored_filename}"
        return stored_filename, public_url

    def delete(self, stored_filename: str) -> None:
        full_path = os.path.join(UPLOAD_DIR, stored_filename)
        if os.path.exists(full_path):
            os.remove(full_path)


# ── AWS S3 stub ───────────────────────────────────────────────────────────────

class S3StorageProvider(StorageProvider):
    """
    Stub for AWS S3 storage.

    Required env vars:
      AWS_ACCESS_KEY_ID
      AWS_SECRET_ACCESS_KEY
      AWS_S3_BUCKET
      AWS_S3_REGION

    Install:  pip install boto3
    """

    async def save(self, file: UploadFile) -> tuple[str, str]:
        raise NotImplementedError(
            "S3StorageProvider is not yet implemented. "
            "See storage.py for instructions."
        )

    def delete(self, stored_filename: str) -> None:
        raise NotImplementedError(
            "S3StorageProvider is not yet implemented. "
            "See storage.py for instructions."
        )


# ── Supabase Storage ──────────────────────────────────────────────────────────

class SupabaseStorageProvider(StorageProvider):
    """
    Production-ready Supabase Storage provider.

    Required env vars (set in Replit Secrets):
      SUPABASE_URL             — https://<project-id>.supabase.co
      SUPABASE_SERVICE_ROLE_KEY — service_role key (NOT the anon key)
      SUPABASE_BUCKET          — storage bucket name (default: papers)

    The bucket must exist in Supabase Storage and be configured as PUBLIC
    so that public_url links work for students to view/download PDFs.

    stored_filename — the UUID-based path stored in papers.file_path
    public_url      — the Supabase public CDN URL stored in papers.public_url
    """

    def __init__(self):
        supabase_url = os.environ.get("SUPABASE_URL", "")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        self._bucket = os.environ.get("SUPABASE_BUCKET", "papers")

        if not supabase_url or not service_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
                "when STORAGE_BACKEND=supabase. Add them to Replit Secrets."
            )

        try:
            from supabase import create_client
            self._client = create_client(supabase_url, service_key)
        except ImportError:
            raise RuntimeError(
                "supabase package is not installed. "
                "Run: pip install supabase"
            )

        logger.info(
            "SupabaseStorageProvider initialised — bucket: %s", self._bucket
        )

    async def save(self, file: UploadFile) -> tuple[str, str]:
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE_MB} MB.",
            )

        ext = file.filename.rsplit(".", 1)[-1].lower()
        stored_filename = f"{uuid.uuid4().hex}.{ext}"

        try:
            self._client.storage.from_(self._bucket).upload(
                path=stored_filename,
                file=content,
                file_options={"content-type": "application/pdf", "upsert": "false"},
            )
        except Exception as exc:
            logger.error("Supabase upload failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail=f"File upload to Supabase failed: {exc}",
            )

        try:
            public_url = (
                self._client.storage
                .from_(self._bucket)
                .get_public_url(stored_filename)
            )
        except Exception as exc:
            logger.error("Supabase get_public_url failed: %s", exc)
            public_url = (
                f"{os.environ.get('SUPABASE_URL', '')}/storage/v1/object/public"
                f"/{self._bucket}/{stored_filename}"
            )

        logger.info("Uploaded %s → %s", stored_filename, public_url)
        return stored_filename, public_url

    def delete(self, stored_filename: str) -> None:
        if not stored_filename:
            return
        try:
            self._client.storage.from_(self._bucket).remove([stored_filename])
            logger.info("Deleted %s from Supabase bucket %s", stored_filename, self._bucket)
        except Exception as exc:
            logger.warning(
                "Supabase delete failed for %s: %s (continuing)", stored_filename, exc
            )


# ── Registry & factory ────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type[StorageProvider]] = {
    "local": LocalStorageProvider,
    "s3": S3StorageProvider,
    "supabase": SupabaseStorageProvider,
}


def get_storage_provider() -> StorageProvider:
    """Return the provider configured by STORAGE_BACKEND env var."""
    cls = _PROVIDERS.get(STORAGE_BACKEND)
    if cls is None:
        raise ValueError(
            f"Unknown STORAGE_BACKEND={STORAGE_BACKEND!r}. "
            f"Valid values: {list(_PROVIDERS.keys())}"
        )
    return cls()


# Singleton — instantiated once at import time.
_provider: StorageProvider = get_storage_provider()


# ── File validation ───────────────────────────────────────────────────────────

def validate_file(file: UploadFile) -> None:
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")


# ── Public API ────────────────────────────────────────────────────────────────
# admin.py imports these names — they stay the same regardless of provider.

async def save_file_locally(file: UploadFile) -> tuple[str, str]:
    """Validate and save an uploaded file. Returns (stored_filename, public_url)."""
    validate_file(file)
    return await _provider.save(file)


def delete_file_locally(stored_filename: str) -> None:
    """Delete a previously saved file by its stored filename."""
    _provider.delete(stored_filename)
