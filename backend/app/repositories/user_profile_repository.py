"""
User Profile repository — direct PostgreSQL access for user accounts, display names, and roles.
"""

import logging
from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UserProfileRepository:
    """Data access layer for user profile management."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_firebase_uid(self, firebase_uid: str) -> dict[str, Any] | None:
        """Fetch user by firebase_uid."""
        stmt = text(
            """
            SELECT id, firebase_uid, email, display_name, role, is_active, created_at, updated_at
            FROM users
            WHERE firebase_uid = :uid
            """
        )
        row = self._db.execute(stmt, {"uid": firebase_uid}).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def update_display_name(self, firebase_uid: str, display_name: str) -> dict[str, Any]:
        """Update user's public display/contribution name."""
        stmt = text(
            """
            UPDATE users
            SET display_name = :display_name, updated_at = NOW()
            WHERE firebase_uid = :uid
            RETURNING id, firebase_uid, email, display_name, role, is_active, created_at, updated_at
            """
        )
        result = self._db.execute(stmt, {"uid": firebase_uid, "display_name": display_name})
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError(f"Failed to update display name for user {firebase_uid}")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d
