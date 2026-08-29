"""
Analytics repository — direct PostgreSQL data access for usage events and dashboard aggregations.

Uses SQLAlchemy Session with parameterized SQL.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Data access layer for analytics events and aggregated telemetry."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def insert_event(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        firebase_uid: Optional[str] = None,
        paper_id: Optional[int] = None,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Insert an analytics event record."""
        stmt = text(
            """
            INSERT INTO analytics_events (
                event_type, session_id, firebase_uid, paper_id, class_id, subject_id, metadata, created_at
            )
            VALUES (
                :event_type, :session_id, :firebase_uid, :paper_id, :class_id, :subject_id, :metadata::jsonb, NOW()
            )
            """
        )
        try:
            self._db.execute(
                stmt,
                {
                    "event_type": event_type,
                    "session_id": session_id,
                    "firebase_uid": firebase_uid,
                    "paper_id": paper_id,
                    "class_id": class_id,
                    "subject_id": subject_id,
                    "metadata": json.dumps(metadata or {}),
                },
            )
            self._db.commit()
            return True
        except Exception as e:
            logger.warning("Failed to insert analytics event: %s", e)
            self._db.rollback()
            return False

    def get_period_stats(self, since: Optional[datetime] = None) -> dict[str, int]:
        """Aggregate visitors, page views, paper views, downloads, searches, likes, comments for a timeframe."""
        where = "WHERE created_at >= :since" if since else ""
        params = {"since": since} if since else {}

        stmt = text(
            f"""
            SELECT
                COUNT(DISTINCT COALESCE(session_id, firebase_uid, id::text))::int AS visitors,
                COUNT(*) FILTER (WHERE event_type = 'page_view')::int AS page_views,
                COUNT(*) FILTER (WHERE event_type = 'paper_view')::int AS paper_views,
                COUNT(*) FILTER (WHERE event_type = 'download')::int AS downloads,
                COUNT(*) FILTER (WHERE event_type = 'search')::int AS searches,
                COUNT(*) FILTER (WHERE event_type = 'like')::int AS likes,
                COUNT(*) FILTER (WHERE event_type = 'comment')::int AS comments
            FROM analytics_events
            {where}
            """
        )
        try:
            result = self._db.execute(stmt, params).fetchone()
            if not result:
                return {"visitors": 0, "page_views": 0, "paper_views": 0, "downloads": 0, "searches": 0, "likes": 0, "comments": 0}
            return dict(result._mapping)
        except Exception as e:
            logger.warning("Period stats aggregation failed: %s", e)
            return {"visitors": 0, "page_views": 0, "paper_views": 0, "downloads": 0, "searches": 0, "likes": 0, "comments": 0}

    def get_top_viewed_papers(self, limit: int = 5, since: Optional[datetime] = None) -> list[dict[str, Any]]:
        """Get top viewed papers from analytics joined with papers table."""
        where_ae = "AND ae.created_at >= :since" if since else ""
        params: dict[str, Any] = {"limit": limit}
        if since:
            params["since"] = since

        stmt = text(
            f"""
            SELECT p.id, p.title AS name, COUNT(ae.id)::int AS count
            FROM analytics_events ae
            JOIN papers p ON ae.paper_id = p.id
            WHERE ae.event_type = 'paper_view' {where_ae}
            GROUP BY p.id, p.title
            ORDER BY count DESC
            LIMIT :limit
            """
        )
        try:
            res = self._db.execute(stmt, params).fetchall()
            return [dict(r._mapping) for r in res]
        except Exception as e:
            logger.warning("Top viewed papers query failed: %s", e)
            return []

    def get_top_downloaded_papers(self, limit: int = 5, since: Optional[datetime] = None) -> list[dict[str, Any]]:
        """Get top downloaded papers from analytics joined with papers table."""
        where_ae = "AND ae.created_at >= :since" if since else ""
        params: dict[str, Any] = {"limit": limit}
        if since:
            params["since"] = since

        stmt = text(
            f"""
            SELECT p.id, p.title AS name, COUNT(ae.id)::int AS count
            FROM analytics_events ae
            JOIN papers p ON ae.paper_id = p.id
            WHERE ae.event_type = 'download' {where_ae}
            GROUP BY p.id, p.title
            ORDER BY count DESC
            LIMIT :limit
            """
        )
        try:
            res = self._db.execute(stmt, params).fetchall()
            return [dict(r._mapping) for r in res]
        except Exception as e:
            logger.warning("Top downloaded papers query failed: %s", e)
            return []

    def get_top_classes(self, limit: int = 5) -> list[dict[str, Any]]:
        """Top classes by page/paper views."""
        stmt = text(
            """
            SELECT c.id, c.name, COUNT(ae.id)::int AS count
            FROM analytics_events ae
            JOIN classes c ON ae.class_id = c.id
            GROUP BY c.id, c.name
            ORDER BY count DESC
            LIMIT :limit
            """
        )
        try:
            res = self._db.execute(stmt, {"limit": limit}).fetchall()
            return [dict(r._mapping) for r in res]
        except Exception as e:
            logger.warning("Top classes query failed: %s", e)
            return []

    def get_top_subjects(self, limit: int = 5) -> list[dict[str, Any]]:
        """Top subjects by page/paper views."""
        stmt = text(
            """
            SELECT s.id, s.name, COUNT(ae.id)::int AS count
            FROM analytics_events ae
            JOIN subjects s ON ae.subject_id = s.id
            GROUP BY s.id, s.name
            ORDER BY count DESC
            LIMIT :limit
            """
        )
        try:
            res = self._db.execute(stmt, {"limit": limit}).fetchall()
            return [dict(r._mapping) for r in res]
        except Exception as e:
            logger.warning("Top subjects query failed: %s", e)
            return []

    def get_top_searches(self, limit: int = 5) -> list[dict[str, Any]]:
        """Top search terms."""
        stmt = text(
            """
            SELECT LOWER(TRIM(metadata->>'q')) AS name, COUNT(*)::int AS count
            FROM analytics_events
            WHERE event_type = 'search' AND metadata->>'q' IS NOT NULL AND TRIM(metadata->>'q') != ''
            GROUP BY LOWER(TRIM(metadata->>'q'))
            ORDER BY count DESC
            LIMIT :limit
            """
        )
        try:
            res = self._db.execute(stmt, {"limit": limit}).fetchall()
            return [dict(r._mapping) for r in res]
        except Exception as e:
            logger.warning("Top searches query failed: %s", e)
            return []

    def get_daily_trends(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily counts for visitors, page views, paper views, downloads."""
        stmt = text(
            """
            SELECT
                TO_CHAR(created_at, 'YYYY-MM-DD') AS date,
                COUNT(DISTINCT COALESCE(session_id, firebase_uid, id::text))::int AS visitors,
                COUNT(*) FILTER (WHERE event_type = 'page_view')::int AS page_views,
                COUNT(*) FILTER (WHERE event_type = 'paper_view')::int AS paper_views,
                COUNT(*) FILTER (WHERE event_type = 'download')::int AS downloads
            FROM analytics_events
            WHERE created_at >= NOW() - (:days || ' days')::INTERVAL
            GROUP BY TO_CHAR(created_at, 'YYYY-MM-DD')
            ORDER BY date ASC
            """
        )
        try:
            res = self._db.execute(stmt, {"days": days}).fetchall()
            return [dict(r._mapping) for r in res]
        except Exception as e:
            logger.warning("Daily trends query failed: %s", e)
            return []
