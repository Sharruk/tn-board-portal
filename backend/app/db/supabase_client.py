"""
Supabase client — singleton pattern.

Usage anywhere in the application:
    from app.db.supabase_client import get_supabase_client

    client = get_supabase_client()
    response = client.table("papers").select("*").execute()
"""

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Return a cached Supabase client singleton.

    The client is created once and reused across all requests.
    Uses the anon key by default — suitable for public read operations
    protected by Supabase RLS.

    For admin operations that bypass RLS, pass SUPABASE_SERVICE_ROLE_KEY
    instead. See get_supabase_admin_client() below.
    """
    settings = get_settings()
    logger.info("Initialising Supabase client (url=%s)", settings.SUPABASE_URL)
    client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    logger.info("Supabase client initialised successfully")
    return client


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """
    Return a Supabase client that uses the service role key.

    WARNING: This client bypasses Row Level Security. Use only for
    trusted server-side operations (bulk imports, admin APIs, etc.).
    Never expose this client to public routes.
    """
    settings = get_settings()
    
    url_present = bool(settings.SUPABASE_URL)
    key_present = bool(settings.SUPABASE_SERVICE_ROLE_KEY)
    
    print(f"[DIAGNOSTIC] SUPABASE_URL configured: {url_present}", flush=True)
    print(f"[DIAGNOSTIC] SUPABASE_SERVICE_ROLE_KEY configured: {key_present}", flush=True)
    
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        print("[DIAGNOSTIC] Admin Supabase client initialization: FAILURE (Missing key)", flush=True)
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. "
            "Admin client cannot be created without it."
        )
    logger.info("Initialising Supabase admin client (url=%s)", settings.SUPABASE_URL)
    
    try:
        client: Client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )
        print("[DIAGNOSTIC] Admin Supabase client initialization: SUCCESS", flush=True)
    except Exception as exc:
        print(f"[DIAGNOSTIC] Admin Supabase client initialization: FAILURE", flush=True)
        print(f"[DIAGNOSTIC] Exception type: {type(exc).__name__}", flush=True)
        print(f"[DIAGNOSTIC] Exception message: {str(exc)}", flush=True)
        raise

    logger.info("Supabase admin client initialised successfully")
    return client
