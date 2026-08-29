"""
Subjects repository — direct PostgreSQL data access for the `subjects` table.

Uses SQLAlchemy Session with parameterized SQL.
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SubjectsRepository:
    """Data access layer for the `subjects` table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[dict[str, Any]]:
        """
        Return all subjects across all classes,
        ordered by class_id then display_order.
        """
        logger.debug("SubjectsRepository.list_all()")
        stmt = text(
            """
            SELECT 
                s.id, s.name, s.slug, s.is_practical, s.display_order, s.class_id,
                c.name AS class_name, c.slug AS class_slug,
                COUNT(p.id)::int AS paper_count
            FROM subjects s
            JOIN classes c ON s.class_id = c.id
            LEFT JOIN papers p ON s.id = p.subject_id AND p.is_visible = true
            GROUP BY s.id, s.name, s.slug, s.is_practical, s.display_order, s.class_id, c.name, c.slug
            ORDER BY s.class_id, s.display_order
            """
        )
        result = self._db.execute(stmt)
        return [dict(row._mapping) for row in result.fetchall()]

    def list_by_class(self, class_id: int) -> list[dict[str, Any]]:
        """
        Return all subjects for a given class_id,
        ordered by display_order.
        """
        logger.debug("SubjectsRepository.list_by_class(class_id=%s)", class_id)
        stmt = text(
            """
            SELECT 
                s.id, s.name, s.slug, s.is_practical, s.display_order, s.class_id,
                c.name AS class_name, c.slug AS class_slug,
                COUNT(p.id)::int AS paper_count
            FROM subjects s
            JOIN classes c ON s.class_id = c.id
            LEFT JOIN papers p ON s.id = p.subject_id AND p.is_visible = true
            WHERE s.class_id = :class_id
            GROUP BY s.id, s.name, s.slug, s.is_practical, s.display_order, s.class_id, c.name, c.slug
            ORDER BY s.display_order
            """
        )
        result = self._db.execute(stmt, {"class_id": class_id})
        return [dict(row._mapping) for row in result.fetchall()]

    def get_by_id(self, subject_id: int) -> dict[str, Any] | None:
        """
        Return a single subject by primary key, or None if not found.
        """
        logger.debug("SubjectsRepository.get_by_id(subject_id=%s)", subject_id)
        stmt = text(
            """
            SELECT 
                s.id, s.name, s.slug, s.is_practical, s.display_order, s.class_id,
                c.name AS class_name, c.slug AS class_slug,
                COUNT(p.id)::int AS paper_count
            FROM subjects s
            JOIN classes c ON s.class_id = c.id
            LEFT JOIN papers p ON s.id = p.subject_id AND p.is_visible = true
            WHERE s.id = :subject_id
            GROUP BY s.id, s.name, s.slug, s.is_practical, s.display_order, s.class_id, c.name, c.slug
            """
        )
        result = self._db.execute(stmt, {"subject_id": subject_id})
        row = result.fetchone()
        if not row:
            return None
        return dict(row._mapping)
