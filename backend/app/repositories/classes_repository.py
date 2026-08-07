"""
Classes repository — all Supabase data access for the `classes` table.

This is the ONLY layer that knows about Supabase.
Services call these methods; routes never call Supabase directly.

Query strategy mirrors the frontend services/classes.js exactly:
  - list:        SELECT *, subjects(count) ORDER BY id
  - get_by_id:   SELECT *, subjects(count) WHERE id = $1 SINGLE
"""

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

# Supabase PostgREST select string — joins aggregate subject count.
_SELECT = "*, subjects(count)"


class ClassesRepository:
    """Data access layer for the `classes` table."""

    def __init__(self, db: Client) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def list_all(self) -> list[dict[str, Any]]:
        """
        Return all classes ordered by id (9, 10, 11, 12),
        each row including a subject count aggregate.
        """
        logger.debug("ClassesRepository.list_all()")
        response = (
            self._db.table("classes")
            .select(_SELECT)
            .order("id")
            .execute()
        )
        return self._normalise_list(response.data)

    def get_by_id(self, class_id: int) -> dict[str, Any] | None:
        """
        Return a single class by its primary key, or None if not found.
        """
        logger.debug("ClassesRepository.get_by_id(class_id=%s)", class_id)
        response = (
            self._db.table("classes")
            .select(_SELECT)
            .eq("id", class_id)
            .execute()
        )
        if not response.data:
            return None
        return self._normalise_row(response.data[0])

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise_row(row: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten the subjects aggregate count onto the row,
        then remove the raw nested list.

        Supabase returns: {"id": 10, ..., "subjects": [{"count": 5}]}
        We want:         {"id": 10, ..., "subject_count": 5}
        """
        subject_count = 0
        if row.get("subjects"):
            subject_count = row["subjects"][0].get("count", 0)
        return {
            "id": row["id"],
            "name": row["name"],
            "slug": row["slug"],
            "subject_count": subject_count,
        }

    @classmethod
    def _normalise_list(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [cls._normalise_row(r) for r in rows]
