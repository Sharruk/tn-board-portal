"""
FastAPI dependency: Supabase client injection.

Usage in a route:
    from app.dependencies.supabase import get_db

    @router.get("/example")
    async def example(db: Client = Depends(get_db)):
        ...

Using Depends() makes the client mockable in tests — just override
the dependency in the TestClient without touching production code.
"""

from supabase import Client

from app.db.supabase_client import get_supabase_client


def get_db() -> Client:
    """Return the application Supabase client singleton."""
    return get_supabase_client()
