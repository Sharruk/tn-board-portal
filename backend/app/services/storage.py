"""
Storage Service
===============
Abstracts file storage so the business logic in admin.py stays unchanged
when swapping providers.

SWAPPING PROVIDERS
------------------
1. Implement the StorageProvider interface below.
2. Register the new class in _PROVIDERS.
3. Set STORAGE_BACKEND=<name> in your .env.

Current providers
-----------------
  local     — saves to /uploads/ on the local filesystem (default, dev only)
  s3        — stub for AWS S3 (fill in S3StorageProvider)
  supabase  — stub for Supabase Storage (fill in SupabaseStorageProvider)

WARNING: "local" storage is ephemeral on Replit managed VMs.
         Switch to s3 or supabase before going live.
"""

import os
import uuid
from abc import ABC, abstractmethod
from fastapi import UploadFile, HTTPException
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, STORAGE_BACKEND


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

    Required env vars (set in .env):
      AWS_ACCESS_KEY_ID
      AWS_SECRET_ACCESS_KEY
      AWS_S3_BUCKET
      AWS_S3_REGION

    Install:  pip install boto3

    Implementation guide — replace the NotImplementedError bodies:

        import boto3, os

        _s3 = boto3.client(
            "s3",
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            region_name=os.environ["AWS_S3_REGION"],
        )
        _bucket = os.environ["AWS_S3_BUCKET"]
        _region = os.environ["AWS_S3_REGION"]

        # In save():
        _s3.put_object(
            Bucket=_bucket,
            Key=stored_filename,
            Body=content,
            ContentType="application/pdf",
        )
        public_url = f"https://{_bucket}.s3.{_region}.amazonaws.com/{stored_filename}"
        return stored_filename, public_url

        # In delete():
        _s3.delete_object(Bucket=_bucket, Key=stored_filename)
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


# ── Supabase Storage stub ─────────────────────────────────────────────────────

class SupabaseStorageProvider(StorageProvider):
    """
    Stub for Supabase Storage.

    Required env vars (set in .env):
      SUPABASE_URL
      SUPABASE_SERVICE_KEY
      SUPABASE_STORAGE_BUCKET

    Install:  pip install supabase

    Implementation guide — replace the NotImplementedError bodies:

        import os
        from supabase import create_client

        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"],
        )
        _bucket = os.environ["SUPABASE_STORAGE_BUCKET"]

        # In save():
        _supabase.storage.from_(_bucket).upload(
            path=stored_filename,
            file=content,
            file_options={"content-type": "application/pdf"},
        )
        public_url = (
            _supabase.storage.from_(_bucket).get_public_url(stored_filename)
        )
        return stored_filename, public_url

        # In delete():
        _supabase.storage.from_(_bucket).remove([stored_filename])
    """

    async def save(self, file: UploadFile) -> tuple[str, str]:
        raise NotImplementedError(
            "SupabaseStorageProvider is not yet implemented. "
            "See storage.py for instructions."
        )

    def delete(self, stored_filename: str) -> None:
        raise NotImplementedError(
            "SupabaseStorageProvider is not yet implemented. "
            "See storage.py for instructions."
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
