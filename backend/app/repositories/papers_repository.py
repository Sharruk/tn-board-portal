"""
Papers repository — all Supabase data access for the `papers` table
and associated RPCs.

This is the ONLY layer that calls Supabase for papers.
Services call these methods; routes never touch Supabase directly.

RPC inventory (all pre-existing — we call, never recreate):
  search_papers(q, p_class_id, p_exam_type, p_paper_type, p_month, p_district)
    → Defined in migration 006, extended in 007, 014, 016.
    → Returns enriched rows with subject_name, class_name, month, district.

  increment_download_count(paper_id_param)
    → Atomically increments download_count for a published paper.
    → Defined in migration 004, updated in 007.

Direct table queries (PostgREST):
  get_by_id       → papers + subjects(*) + classes(*)   WHERE id = $1
  list_recent     → papers WHERE status = published ORDER BY created_at DESC LIMIT N
  list_popular    → papers WHERE status = published ORDER BY download_count DESC LIMIT N
  list_by_subject → papers WHERE subject_id = $1 AND status = published

Query strategy mirrors frontend/src/services/papers.js and subjects.js exactly.
"""

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

# PostgREST select string for the full paper detail (mirrors getPaper in papers.js)
_DETAIL_SELECT = "*, subjects ( id, name, slug, is_practical, classes ( id, name, slug ) )"

# Select string for list endpoints (no internal file_path)
_LIST_SELECT = (
    "id, subject_id, exam_type, year, month, district, title, paper_type, "
    "public_url, youtube_url, original_filename, is_visible, status, "
    "download_count, created_at"
)


class PapersRepository:
    """Data access layer for the `papers` table and papers RPCs."""

    def __init__(self, db: Client) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Single paper
    # ------------------------------------------------------------------ #

    def get_by_id(self, paper_id: int, published_only: bool = True) -> dict[str, Any] | None:
        """
        Return one paper with full subject + class join, or None.

        Args:
            paper_id:       Primary key.
            published_only: When True, only return status='published' papers.
                            Set False for admin reads (Sprint 06+).
        """
        logger.debug("PapersRepository.get_by_id(paper_id=%s)", paper_id)
        query = (
            self._db.table("papers")
            .select(_DETAIL_SELECT)
            .eq("id", paper_id)
        )
        if published_only:
            query = query.eq("status", "published")

        response = query.execute()
        if not response.data:
            return None
        return self._normalise_detail(response.data[0])

    # ------------------------------------------------------------------ #
    # List endpoints
    # ------------------------------------------------------------------ #

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the N most recently uploaded published papers.
        Mirrors getRecentPapers() in frontend/src/services/papers.js.
        """
        logger.debug("PapersRepository.list_recent(limit=%s)", limit)
        response = (
            self._db.table("papers")
            .select(_LIST_SELECT)
            .eq("status", "published")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def list_popular(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the N most downloaded published papers.
        Mirrors getPopularPapers() in frontend/src/services/papers.js.
        """
        logger.debug("PapersRepository.list_popular(limit=%s)", limit)
        response = (
            self._db.table("papers")
            .select(_LIST_SELECT)
            .eq("status", "published")
            .order("download_count", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def list_by_subject(
        self,
        subject_id: int,
        exam_type: str | None = None,
        paper_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return all published papers for a given subject.
        Mirrors getPapersForSubject() in frontend/src/services/subjects.js.

        Args:
            subject_id:  Filter by subject.
            exam_type:   Optional exam type filter.
            paper_type:  Optional paper type filter ('question' | 'answer_key').
        """
        logger.debug(
            "PapersRepository.list_by_subject(subject_id=%s, exam_type=%s, paper_type=%s)",
            subject_id, exam_type, paper_type,
        )
        query = (
            self._db.table("papers")
            .select(_LIST_SELECT)
            .eq("subject_id", subject_id)
            .eq("status", "published")
            .order("year", desc=True)
        )
        if exam_type:
            query = query.eq("exam_type", exam_type)
        if paper_type:
            query = query.eq("paper_type", paper_type)

        response = query.execute()
        return response.data or []

    # ------------------------------------------------------------------ #
    # Search RPC
    # ------------------------------------------------------------------ #

    def search(
        self,
        q: str,
        class_id: int | None = None,
        exam_type: str | None = None,
        paper_type: str | None = None,
        month: str | None = None,
        district: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Call the search_papers() Supabase RPC.

        Uses the exact 6-parameter signature defined in migration 016:
          search_papers(q, p_class_id, p_exam_type, p_paper_type, p_month, p_district)

        All filter params default to NULL (no filter) — exactly as the
        original function was designed.

        NOTE: Term expansion (aliases like 'maths' → 'mathematics') is a
        business-logic concern and lives in PapersService, not here.
        """
        logger.debug(
            "PapersRepository.search(q=%r, class_id=%s, exam_type=%s, paper_type=%s, month=%s, district=%s)",
            q, class_id, exam_type, paper_type, month, district,
        )
        response = self._db.rpc(
            "search_papers",
            {
                "q":            q,
                "p_class_id":   class_id,
                "p_exam_type":  exam_type,
                "p_paper_type": paper_type,
                "p_month":      month,
                "p_district":   district,
            },
        ).execute()
        return response.data or []

    # ------------------------------------------------------------------ #
    # Download tracking RPC
    # ------------------------------------------------------------------ #

    def record_download(self, paper_id: int) -> None:
        """
        Atomically increment download_count for a published paper.
        Calls the increment_download_count() RPC defined in migration 004/007.
        Raises if the paper is not published (Supabase raises an exception).
        """
        logger.debug("PapersRepository.record_download(paper_id=%s)", paper_id)
        self._db.rpc(
            "increment_download_count",
            {"paper_id_param": paper_id},
        ).execute()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise_detail(row: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten the nested subjects → classes join into flat fields.

        Supabase returns:
            {
              "id": 42,
              "subjects": {
                "id": 8, "name": "Mathematics", "slug": "maths",
                "is_practical": false,
                "classes": { "id": 10, "name": "Class 10", "slug": "10" }
              }
            }
        We want:
            {
              "id": 42,
              "subject_name": "Mathematics", "subject_slug": "maths",
              "is_practical": false,
              "class_id": 10, "class_name": "Class 10", "class_slug": "10"
            }
        """
        subjects = row.pop("subjects", None) or {}
        classes  = subjects.pop("classes", None) or {}
        return {
            **row,
            "subject_name": subjects.get("name"),
            "subject_slug": subjects.get("slug"),
            "is_practical": subjects.get("is_practical"),
            "class_id":     classes.get("id"),
            "class_name":   classes.get("name"),
            "class_slug":   classes.get("slug"),
        }
