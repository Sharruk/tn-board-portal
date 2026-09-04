"""
Conversations repository — PostgreSQL data access for student-admin messaging.
"""

import logging
from typing import Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ConversationsRepository:
    """Data access layer for conversations and messages."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_conversation(
        self,
        firebase_uid: str,
        user_email: str,
        user_display_name: str,
        category: str,
        subject: str,
        initial_message: str,
        submission_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Insert a new conversation and its first message atomically."""
        conv_stmt = text(
            """
            INSERT INTO conversations (
                firebase_uid, user_email, user_display_name, category, subject,
                status, submission_id, created_at, updated_at
            )
            VALUES (
                :uid, :email, :display_name, :category, :subject,
                'awaiting_admin', :submission_id, NOW(), NOW()
            )
            RETURNING id, firebase_uid, user_email, user_display_name, category, subject, status, submission_id, created_at, updated_at
            """
        )
        conv_res = self._db.execute(
            conv_stmt,
            {
                "uid": firebase_uid,
                "email": user_email,
                "display_name": user_display_name,
                "category": category,
                "subject": subject,
                "submission_id": submission_id,
            },
        )
        conv_row = conv_res.fetchone()
        if not conv_row:
            raise RuntimeError("Failed to create conversation record.")

        conv_dict = dict(conv_row._mapping)
        conv_id = str(conv_dict["id"])
        conv_dict["id"] = conv_id
        if conv_dict.get("submission_id"):
            conv_dict["submission_id"] = str(conv_dict["submission_id"])

        # Insert initial message
        msg_stmt = text(
            """
            INSERT INTO messages (
                conversation_id, sender_role, sender_firebase_uid, sender_name,
                message, is_read, created_at
            )
            VALUES (
                :conv_id, 'user', :uid, :display_name,
                :message, false, NOW()
            )
            RETURNING id, conversation_id, sender_role, sender_firebase_uid, sender_name, message, is_read, read_at, created_at
            """
        )
        msg_res = self._db.execute(
            msg_stmt,
            {
                "conv_id": conv_id,
                "uid": firebase_uid,
                "display_name": user_display_name,
                "message": initial_message,
            },
        )
        self._db.commit()
        msg_row = msg_res.fetchone()
        msg_dict = dict(msg_row._mapping) if msg_row else {}
        if msg_dict:
            msg_dict["id"] = str(msg_dict["id"])
            msg_dict["conversation_id"] = str(msg_dict["conversation_id"])

        conv_dict["messages"] = [msg_dict] if msg_dict else []
        return conv_dict

    def get_conversation_by_id(self, conversation_id: str) -> Optional[dict[str, Any]]:
        """Fetch a single conversation by UUID."""
        stmt = text(
            """
            SELECT c.id, c.firebase_uid, c.user_email, c.user_display_name, c.category,
                   c.subject, c.status, c.submission_id, c.created_at, c.updated_at,
                   u.photo_url AS user_photo_url
            FROM conversations c
            LEFT JOIN users u ON u.firebase_uid = c.firebase_uid
            WHERE c.id = :cid
            """
        )
        row = self._db.execute(stmt, {"cid": conversation_id}).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        if d.get("submission_id"):
            d["submission_id"] = str(d["submission_id"])
        return d

    def get_messages(self, conversation_id: str) -> List[dict[str, Any]]:
        """Fetch all messages for a conversation ordered chronologically."""
        stmt = text(
            """
            SELECT id, conversation_id, sender_role, sender_firebase_uid, sender_name,
                   message, is_read, read_at, created_at
            FROM messages
            WHERE conversation_id = :cid
            ORDER BY created_at ASC
            """
        )
        rows = self._db.execute(stmt, {"cid": conversation_id}).fetchall()
        result = []
        for r in rows:
            m = dict(r._mapping)
            m["id"] = str(m["id"])
            m["conversation_id"] = str(m["conversation_id"])
            result.append(m)
        return result

    def add_message(
        self,
        conversation_id: str,
        sender_role: str,
        sender_firebase_uid: str,
        sender_name: str,
        message: str,
        new_status: Optional[str] = None,
    ) -> dict[str, Any]:
        """Append a message to an existing conversation and update conversation timestamps."""
        msg_stmt = text(
            """
            INSERT INTO messages (
                conversation_id, sender_role, sender_firebase_uid, sender_name,
                message, is_read, created_at
            )
            VALUES (
                :conv_id, :sender_role, :uid, :sender_name,
                :message, false, NOW()
            )
            RETURNING id, conversation_id, sender_role, sender_firebase_uid, sender_name, message, is_read, read_at, created_at
            """
        )
        msg_res = self._db.execute(
            msg_stmt,
            {
                "conv_id": conversation_id,
                "sender_role": sender_role,
                "uid": sender_firebase_uid,
                "sender_name": sender_name,
                "message": message,
            },
        )
        msg_row = msg_res.fetchone()
        if not msg_row:
            raise RuntimeError("Failed to insert message.")

        # Determine conversation status change
        if not new_status:
            new_status = "awaiting_admin" if sender_role == "user" else "awaiting_user"

        upd_stmt = text(
            """
            UPDATE conversations
            SET status = :status, updated_at = NOW()
            WHERE id = :cid
            """
        )
        self._db.execute(upd_stmt, {"status": new_status, "cid": conversation_id})
        self._db.commit()

        d = dict(msg_row._mapping)
        d["id"] = str(d["id"])
        d["conversation_id"] = str(d["conversation_id"])
        return d

    def mark_messages_read(self, conversation_id: str, reader_role: str) -> int:
        """
        Mark messages sent by the counter-party as read.
        If reader_role == 'user', mark admin messages as read.
        If reader_role == 'admin', mark user messages as read.
        """
        target_sender_role = "admin" if reader_role == "user" else "user"
        stmt = text(
            """
            UPDATE messages
            SET is_read = true, read_at = NOW()
            WHERE conversation_id = :cid AND sender_role = :target_role AND is_read = false
            """
        )
        res = self._db.execute(stmt, {"cid": conversation_id, "target_role": target_sender_role})
        self._db.commit()
        return res.rowcount

    def get_user_conversations(
        self, firebase_uid: str, limit: int = 50, offset: int = 0
    ) -> tuple[List[dict[str, Any]], int]:
        """Fetch all conversations initiated by a user with unread counts and latest message."""
        count_stmt = text(
            "SELECT COUNT(*) FROM conversations WHERE firebase_uid = :uid"
        )
        total = self._db.execute(count_stmt, {"uid": firebase_uid}).scalar() or 0

        stmt = text(
            """
            SELECT c.id, c.firebase_uid, c.user_email, c.user_display_name, c.category,
                   c.subject, c.status, c.submission_id, c.created_at, c.updated_at,
                   u.photo_url AS user_photo_url,
                   (
                       SELECT COUNT(*)::int
                       FROM messages m
                       WHERE m.conversation_id = c.id
                         AND m.sender_role = 'admin'
                         AND m.is_read = false
                   ) AS unread_count,
                   (
                       SELECT m.message
                       FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message,
                   (
                       SELECT m.created_at
                       FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_at,
                   (
                       SELECT m.sender_role
                       FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_sender_role
            FROM conversations c
            LEFT JOIN users u ON u.firebase_uid = c.firebase_uid
            WHERE c.firebase_uid = :uid
            ORDER BY c.updated_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        rows = self._db.execute(
            stmt, {"uid": firebase_uid, "limit": limit, "offset": offset}
        ).fetchall()

        items = []
        for r in rows:
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            if d.get("submission_id"):
                d["submission_id"] = str(d["submission_id"])
            items.append(d)
        return items, total

    def get_user_unread_count(self, firebase_uid: str) -> int:
        """Count all unread admin messages across user's conversations."""
        stmt = text(
            """
            SELECT COUNT(*)::int
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE c.firebase_uid = :uid
              AND m.sender_role = 'admin'
              AND m.is_read = false
            """
        )
        return self._db.execute(stmt, {"uid": firebase_uid}).scalar() or 0

    def get_admin_conversations(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[dict[str, Any]], int]:
        """Fetch conversations for Admin Inbox with flexible filtering."""
        where_clauses = ["1=1"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if status:
            if status == "unread":
                where_clauses.append(
                    """
                    EXISTS (
                        SELECT 1 FROM messages m
                        WHERE m.conversation_id = c.id
                          AND m.sender_role = 'user'
                          AND m.is_read = false
                    )
                    """
                )
            else:
                where_clauses.append("c.status = :status")
                params["status"] = status

        if category:
            where_clauses.append("c.category = :category")
            params["category"] = category

        if search:
            where_clauses.append(
                """
                (
                    LOWER(c.subject) LIKE :search
                    OR LOWER(c.user_email) LIKE :search
                    OR LOWER(c.user_display_name) LIKE :search
                )
                """
            )
            params["search"] = f"%{search.strip().lower()}%"

        where_sql = " AND ".join(where_clauses)

        count_stmt = text(f"SELECT COUNT(*) FROM conversations c WHERE {where_sql}")
        total = self._db.execute(count_stmt, params).scalar() or 0

        sql = f"""
            SELECT c.id, c.firebase_uid, c.user_email, c.user_display_name, c.category,
                   c.subject, c.status, c.submission_id, c.created_at, c.updated_at,
                   u.photo_url AS user_photo_url,
                   (
                       SELECT COUNT(*)::int
                       FROM messages m
                       WHERE m.conversation_id = c.id
                         AND m.sender_role = 'user'
                         AND m.is_read = false
                   ) AS unread_count,
                   (
                       SELECT m.message
                       FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message,
                   (
                       SELECT m.created_at
                       FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_at,
                   (
                       SELECT m.sender_role
                       FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY m.created_at DESC
                       LIMIT 1
                   ) AS last_message_sender_role
            FROM conversations c
            LEFT JOIN users u ON u.firebase_uid = c.firebase_uid
            WHERE {where_sql}
            ORDER BY c.updated_at DESC
            LIMIT :limit OFFSET :offset
        """
        rows = self._db.execute(text(sql), params).fetchall()

        items = []
        for r in rows:
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            if d.get("submission_id"):
                d["submission_id"] = str(d["submission_id"])
            items.append(d)
        return items, total

    def get_admin_conversation_stats(self) -> dict[str, int]:
        """Aggregate stats for Admin Inbox tabs."""
        stmt = text(
            """
            SELECT
                COUNT(*)::int AS total,
                COUNT(*) FILTER (
                    WHERE EXISTS (
                        SELECT 1 FROM messages m
                        WHERE m.conversation_id = conversations.id
                          AND m.sender_role = 'user'
                          AND m.is_read = false
                    )
                )::int AS unread_count,
                COUNT(*) FILTER (WHERE status = 'awaiting_admin')::int AS awaiting_admin,
                COUNT(*) FILTER (WHERE status = 'awaiting_user')::int AS awaiting_user,
                COUNT(*) FILTER (WHERE status = 'resolved')::int AS resolved
            FROM conversations
            """
        )
        row = self._db.execute(stmt).fetchone()
        if not row:
            return {"total": 0, "unread_count": 0, "awaiting_admin": 0, "awaiting_user": 0, "resolved": 0}
        return dict(row._mapping)

    def update_status(self, conversation_id: str, new_status: str) -> Optional[dict[str, Any]]:
        """Update conversation status."""
        stmt = text(
            """
            UPDATE conversations
            SET status = :status, updated_at = NOW()
            WHERE id = :cid
            RETURNING id, firebase_uid, user_email, user_display_name, category, subject, status, submission_id, created_at, updated_at
            """
        )
        res = self._db.execute(stmt, {"status": new_status, "cid": conversation_id})
        self._db.commit()
        row = res.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        if d.get("submission_id"):
            d["submission_id"] = str(d["submission_id"])
        return d
