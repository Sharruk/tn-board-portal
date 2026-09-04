"""
Admin Users repository — PostgreSQL data access for Admin User Management.
"""

import logging
from typing import Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AdminUsersRepository:
    """Data access layer for Admin User Management."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_users_list(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[dict[str, Any]], int]:
        """
        Fetch paginated registered users with submission counts.
        """
        where_sql = "1=1"
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if search:
            where_sql = "(LOWER(u.email) LIKE :search OR LOWER(COALESCE(u.display_name, '')) LIKE :search)"
            params["search"] = f"%{search.strip().lower()}%"

        count_stmt = text(f"SELECT COUNT(*) FROM users u WHERE {where_sql}")
        total = self._db.execute(count_stmt, params).scalar() or 0

        sql = f"""
            SELECT
                u.id,
                u.firebase_uid,
                u.email,
                u.display_name,
                u.photo_url,
                u.role,
                u.is_active,
                u.created_at,
                u.last_active_at,
                COALESCE(s.total_submissions, 0) AS total_submissions,
                COALESCE(s.published_count, 0) AS published_count,
                COALESCE(s.pending_count, 0) AS pending_count,
                COALESCE(s.rejected_count, 0) AS rejected_count
            FROM users u
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*)::int AS total_submissions,
                    COUNT(*) FILTER (WHERE LOWER(sub.status) = 'approved')::int AS published_count,
                    COUNT(*) FILTER (WHERE LOWER(sub.status) = 'pending')::int AS pending_count,
                    COUNT(*) FILTER (WHERE LOWER(sub.status) = 'rejected')::int AS rejected_count
                FROM submissions sub
                WHERE sub.firebase_uid = u.firebase_uid
                   OR (sub.firebase_uid IS NULL AND LOWER(sub.email) = LOWER(u.email))
            ) s ON true
            WHERE {where_sql}
            ORDER BY COALESCE(u.last_active_at, u.created_at) DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """
        rows = self._db.execute(text(sql), params).fetchall()
        items = []
        for r in rows:
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            items.append(d)
        return items, total

    def get_summary_counts(self) -> dict[str, int]:
        """Return total registered users and contributors count."""
        stmt = text(
            """
            SELECT
                (SELECT COUNT(*)::int FROM users) AS total_users,
                (SELECT COUNT(DISTINCT COALESCE(firebase_uid, LOWER(email)))::int FROM submissions) AS total_contributors
            """
        )
        row = self._db.execute(stmt).fetchone()
        if not row:
            return {"total_users": 0, "total_contributors": 0}
        d = dict(row._mapping)
        return {
            "total_users": d.get("total_users", 0),
            "total_contributors": d.get("total_contributors", 0),
        }

    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[dict[str, Any]]:
        """Fetch user record and their submission counts."""
        sql = """
            SELECT
                u.id,
                u.firebase_uid,
                u.email,
                u.display_name,
                u.photo_url,
                u.role,
                u.is_active,
                u.created_at,
                u.last_active_at,
                COALESCE(s.total_submissions, 0) AS total_submissions,
                COALESCE(s.published_count, 0) AS published_count,
                COALESCE(s.pending_count, 0) AS pending_count,
                COALESCE(s.rejected_count, 0) AS rejected_count
            FROM users u
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(*)::int AS total_submissions,
                    COUNT(*) FILTER (WHERE LOWER(sub.status) = 'approved')::int AS published_count,
                    COUNT(*) FILTER (WHERE LOWER(sub.status) = 'pending')::int AS pending_count,
                    COUNT(*) FILTER (WHERE LOWER(sub.status) = 'rejected')::int AS rejected_count
                FROM submissions sub
                WHERE sub.firebase_uid = u.firebase_uid
                   OR (sub.firebase_uid IS NULL AND LOWER(sub.email) = LOWER(u.email))
            ) s ON true
            WHERE u.firebase_uid = :uid
        """
        row = self._db.execute(text(sql), {"uid": firebase_uid}).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def get_user_submissions(self, firebase_uid: str, email: Optional[str] = None) -> List[dict[str, Any]]:
        """Fetch all submissions made by a user."""
        sql = """
            SELECT
                s.id,
                s.publisher_name,
                s.details,
                s.status,
                s.rejection_reason,
                s.thank_you_message,
                s.created_at,
                s.reviewed_at,
                (SELECT COUNT(*)::int FROM submission_files sf WHERE sf.submission_id = s.id) AS file_count
            FROM submissions s
            WHERE s.firebase_uid = :uid
        """
        params: dict[str, Any] = {"uid": firebase_uid}
        if email:
            sql += " OR (s.firebase_uid IS NULL AND LOWER(s.email) = LOWER(:email))"
            params["email"] = email

        sql += " ORDER BY s.created_at DESC"
        rows = self._db.execute(text(sql), params).fetchall()

        items = []
        for r in rows:
            d = dict(r._mapping)
            sub_id = str(d["id"])
            d["id"] = sub_id

            # Fetch any published papers linked to this submission
            p_stmt = text("SELECT id, title, year, exam_type FROM papers WHERE submission_id = :sid")
            p_rows = self._db.execute(p_stmt, {"sid": sub_id}).fetchall()
            d["published_papers"] = [dict(pr._mapping) for pr in p_rows]
            items.append(d)
        return items

    def get_user_conversations(self, firebase_uid: str) -> List[dict[str, Any]]:
        """Fetch summary of conversations opened by this user."""
        stmt = text(
            """
            SELECT c.id, c.category, c.subject, c.status, c.updated_at, c.created_at,
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
                   ) AS last_message
            FROM conversations c
            WHERE c.firebase_uid = :uid
            ORDER BY c.updated_at DESC
            """
        )
        rows = self._db.execute(stmt, {"uid": firebase_uid}).fetchall()
        items = []
        for r in rows:
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            items.append(d)
        return items
