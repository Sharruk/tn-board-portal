"""
Admin Team Chat repository — PostgreSQL data access for Admin Group Messaging.
"""

import logging
from typing import Any, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AdminTeamChatRepository:
    """Data access layer for admin_group_messages."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_messages(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[List[dict[str, Any]], int]:
        """Fetch all messages for Admin Team Chat ordered chronologically."""
        count_stmt = text("SELECT COUNT(*) FROM admin_group_messages")
        total = self._db.execute(count_stmt).scalar() or 0

        stmt = text(
            """
            SELECT id, sender_firebase_uid, sender_email, sender_name, sender_role,
                   message, created_at
            FROM admin_group_messages
            ORDER BY created_at ASC, id ASC
            LIMIT :limit OFFSET :offset
            """
        )
        rows = self._db.execute(stmt, {"limit": limit, "offset": offset}).fetchall()
        result = []
        for r in rows:
            m = dict(r._mapping)
            m["id"] = str(m["id"])
            result.append(m)
        return result, total

    def add_message(
        self,
        sender_firebase_uid: str,
        sender_email: str,
        sender_name: str,
        sender_role: str,
        message: str,
    ) -> dict[str, Any]:
        """Insert a new group message atomically."""
        msg_stmt = text(
            """
            INSERT INTO admin_group_messages (
                sender_firebase_uid, sender_email, sender_name, sender_role, message, created_at
            )
            VALUES (
                :uid, :email, :name, :role, :message, NOW()
            )
            RETURNING id, sender_firebase_uid, sender_email, sender_name, sender_role, message, created_at
            """
        )
        res = self._db.execute(
            msg_stmt,
            {
                "uid": sender_firebase_uid,
                "email": sender_email,
                "name": sender_name,
                "role": sender_role,
                "message": message,
            },
        )
        self._db.commit()
        row = res.fetchone()
        if not row:
            raise RuntimeError("Failed to insert admin group message.")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

