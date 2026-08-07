"""
Subjects repository — all Supabase data access for the `subjects` table.

This is the ONLY layer that knows about Supabase.
Services call these methods; routes never call Supabase directly.

Query strategy mirrors the frontend services/subjects.js and
the embedded getSubjectsForClass in services/classes.js:
  - list:          SELECT enriched columns ORDER BY display_order
  - list_by_class: SELECT enriched columns WHERE class_id = $1
  - get_by_id:     SELECT enriched + class info WHERE id = $1 SINGLE
"""

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

# PostgREST select — joins class info and counts available papers.
_SELECT_ENRICHED = (
    "id, name, slug, is_practical, display_order, class_id, "
    "classes ( id, name, slug ), "
    "papers ( count )"
)


class SubjectsRepository:
    """Data access layer for the `subjects` table."""

    def __init__(self, db: Client) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def list_all(self) -> list[dict[str, Any]]:
        """
        Return all subjects across all classes,
        ordered by class_id then display_order.
        """
        logger.debug("SubjectsRepository.list_all()")
        response = (
            self._db.table("subjects")
            .select(_SELECT_ENRICHED)
            .order("class_id")
            .order("display_order")
            .execute()
        )
        return self._normalise_list(response.data)

    def list_by_class(self, class_id: int) -> list[dict[str, Any]]:
        """
        Return all subjects for a given class_id,
        ordered by display_order.
        """
        logger.debug("SubjectsRepository.list_by_class(class_id=%s)", class_id)
        response = (
            self._db.table("subjects")
            .select(_SELECT_ENRICHED)
            .eq("class_id", class_id)
            .order("display_order")
            .execute()
        )
        return self._normalise_list(response.data)

    def get_by_id(self, subject_id: int) -> dict[str, Any] | None:
        """
        Return a single subject by primary key, or None if not found.
        """
        logger.debug("SubjectsRepository.get_by_id(subject_id=%s)", subject_id)
        response = (
            self._db.table("subjects")
            .select(_SELECT_ENRICHED)
            .eq("id", subject_id)
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
        Flatten joined class info and paper aggregate count.

        Supabase returns:
            {
              "id": 8,
              "classes": {"id": 10, "name": "Class 10", "slug": "10"},
              "papers":  [{"count": 12}]
            }
        We want:
            {
              "id": 8,
              "class_name": "Class 10",
              "class_slug": "10",
              "paper_count": 12
            }
        """
        classes = row.get("classes") or {}
        papers = row.get("papers") or []
        return {
            "id": row["id"],
            "class_id": row["class_id"],
            "name": row["name"],
            "slug": row["slug"],
            "is_practical": row["is_practical"],
            "display_order": row["display_order"],
            "class_name": classes.get("name"),
            "class_slug": classes.get("slug"),
            "paper_count": papers[0].get("count", 0) if papers else 0,
        }

    @classmethod
    def _normalise_list(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [cls._normalise_row(r) for r in rows]
