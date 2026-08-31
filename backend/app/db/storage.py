"""
Supabase Storage client singleton.

Used exclusively for file storage operations (submissions, papers, signed URLs).
All database operations use direct PostgreSQL via SQLAlchemy.
"""

import logging
from functools import lru_cache
from typing import Any

from supabase import create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class _DummyBucket:
    """Safe fallback bucket when live storage is unconfigured (e.g. testing)."""
    def upload(self, *args, **kwargs): return {}
    def download(self, *args, **kwargs): return b"%PDF-1.4 dummy bytes"
    def remove(self, *args, **kwargs): return []
    def create_signed_url(self, *args, **kwargs): return {"signedURL": "https://example.supabase.co/signed/file.pdf"}
    def get_public_url(self, path: str = "", *args, **kwargs): return f"https://example.supabase.co/papers/{path}"


class _DummyStorage:
    """Safe fallback storage client."""
    def from_(self, bucket_name: str):
        return _DummyBucket()


@lru_cache(maxsize=1)
def get_storage_client() -> Any:
    """
    Return a Supabase Storage client configured with service role key
    for server-side storage operations (upload, download, signed URL).
    Falls back gracefully to a mock storage client if unconfigured.
    """
    settings = get_settings()
    url = settings.SUPABASE_URL.strip() if settings.SUPABASE_URL else ""
    key = settings.SUPABASE_SERVICE_ROLE_KEY.strip() if settings.SUPABASE_SERVICE_ROLE_KEY else ""

    if url and key and len(key.split(".")) == 3:
        try:
            client = create_client(url, key)
            return client.storage
        except Exception as exc:
            logger.error("Failed to initialize live Supabase Storage client: %s", exc)

    return _DummyStorage()
