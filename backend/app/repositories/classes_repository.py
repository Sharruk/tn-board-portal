"""
Classes repository — direct PostgreSQL data access for the `classes` table.

Uses SQLAlchemy Session with parameterized SQL.
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ClassesRepository:
    """Data access layer for the `classes` table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[dict[str, Any]]:
        """
        Return all classes ordered by id (9, 10, 11, 12),
        each row including a subject count aggregate.
        """
        logger.debug("ClassesRepository.list_all()")
        stmt = text(
            """
            SELECT c.id, c.name, c.slug, COUNT(s.id)::int AS subject_count
            FROM classes c
            LEFT JOIN subjects s ON c.id = s.class_id
            GROUP BY c.id, c.name, c.slug
            ORDER BY c.id
            """
        )
        result = self._db.execute(stmt)
        return [dict(row._mapping) for row in result.fetchall()]

    def get_by_id(self, class_id: int) -> dict[str, Any] | None:
        """
        Return a single class by its primary key, or None if not found.
        """
        logger.debug("ClassesRepository.get_by_id(class_id=%s)", class_id)
        stmt = text(
            """
            SELECT c.id, c.name, c.slug, COUNT(s.id)::int AS subject_count
            FROM classes c
            LEFT JOIN subjects s ON c.id = s.class_id
            WHERE c.id = :class_id
            GROUP BY c.id, c.name, c.slug
            """
        )
        result = self._db.execute(stmt, {"class_id": class_id})
        row = result.fetchone()
        if not row:
            return None
        return dict(row._mapping)
