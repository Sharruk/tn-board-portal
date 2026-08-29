"""
Leaderboard repository — direct PostgreSQL data access for contributor rankings.

Uses SQLAlchemy Session with parameterized SQL.
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LeaderboardRepository:
    """Data access layer for leaderboard calculations from submissions."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_raw_submissions_for_leaderboard(self) -> list[dict[str, Any]]:
        """
        Fetch submission records with file counts needed to compute contributor leaderboard.
        Only reads public identity fields and status (no sensitive info).
        """
        logger.debug("LeaderboardRepository.get_raw_submissions_for_leaderboard()")
        stmt = text(
            """
            SELECT s.id, s.publisher_name, s.firebase_uid, s.status, s.created_at,
                   COALESCE(COUNT(f.id), 1) AS file_count
            FROM submissions s
            LEFT JOIN submission_files f ON s.id = f.submission_id
            GROUP BY s.id, s.publisher_name, s.firebase_uid, s.status, s.created_at
            ORDER BY s.created_at DESC
            """
        )
        try:
            result = self._db.execute(stmt)
            return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.warning("Failed with file_count join, falling back to simple query: %s", e)
            fallback_stmt = text(
                """
                SELECT id, publisher_name, firebase_uid, status, created_at, 1 AS file_count
                FROM submissions
                """
            )
            result = self._db.execute(fallback_stmt)
            return [dict(row._mapping) for row in result.fetchall()]

    def get_recent_approved_papers_for_contributors(self) -> dict[str, list[str]]:
        """Fetch recently approved paper titles grouped by contributor."""
        stmt = text(
            """
            SELECT s.firebase_uid, s.publisher_name, p.title
            FROM papers p
            JOIN submissions s ON (s.firebase_uid IS NOT NULL AND s.status = 'approved')
            WHERE p.is_visible = true
            ORDER BY p.created_at DESC
            LIMIT 50
            """
        )
        try:
            result = self._db.execute(stmt)
            out: dict[str, list[str]] = {}
            for row in result.fetchall():
                key = row.firebase_uid or (row.publisher_name or "").strip().lower()
                if key:
                    out.setdefault(key, []).append(row.title)
            return out
        except Exception as e:
            logger.debug("Recent papers query error (safe to ignore): %s", e)
            return {}
