"""
FastAPI dependency: Database Session injection.

Usage in a route:
    from app.dependencies.supabase import get_db

    @router.get("/example")
    async def example(db: Session = Depends(get_db)):
        ...
"""

from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import get_db

__all__ = ["get_db", "Session"]
