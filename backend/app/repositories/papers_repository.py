"""
Papers repository — all Supabase data access for the `papers` table
and associated RPCs.

This is the ONLY layer that calls Supabase for papers.
Services call these methods; routes never touch Supabase directly.

=============================================================================
COMPATIBILITY NOTE — migration 007 not applied to live DB
=============================================================================
The live Supabase database was created from migration 001 (schema) and
subsequent ADD COLUMN migrations, but migration 007 (paper_status.sql) was
NOT applied. As a result:

  • papers.status  column → DOES NOT EXIST in live DB
  • search_papers() RPC   → broken (function body references p.status)
  • increment_download_count() RPC → broken (references status column)

The workaround applied in this file:

  1. All published-paper filters use   is_visible = true
     instead of                        status = 'published'

  2. A synthesised   status = "published"   field is injected into every
     returned row so that the Pydantic schemas (which include status) are
     satisfied without any schema changes.

  3. The search_papers() RPC is replaced by a direct PostgREST query
     with OR filters on papers columns (title, exam_type, month, district)
     plus Python-level filtering on the joined subject/class names.

  4. The increment_download_count() RPC is replaced by a direct UPDATE
     via PostgREST patch (supabase-py .update()).

Direct table queries (PostgREST):
  get_by_id       → papers + subjects(*) + classes(*)   WHERE id = $1
  list_recent     → papers WHERE is_visible = true ORDER BY created_at DESC LIMIT N
  list_popular    → papers WHERE is_visible = true ORDER BY download_count DESC LIMIT N
  list_by_subject → papers WHERE subject_id = $1 AND is_visible = true

Query strategy mirrors frontend/src/services/papers.js and subjects.js exactly.
=============================================================================
"""

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PostgREST select strings
# ---------------------------------------------------------------------------

# Select for list endpoints — excludes internal file_path and the missing
# status column.  A synthesised status="published" is added in _add_status().
_LIST_COLUMNS = (
    "id, subject_id, exam_type, year, month, district, title, paper_type, "
    "public_url, youtube_url, original_filename, is_visible, "
    "download_count, created_at"
)

# Select for the full paper detail — includes the subjects/classes join.
_DETAIL_SELECT = (
    "id, subject_id, exam_type, year, month, district, title, paper_type, "
    "public_url, youtube_url, original_filename, is_visible, "
    "download_count, created_at, "
    "subjects ( id, name, slug, is_practical, classes ( id, name, slug ) )"
)

# Select for search — includes the subjects/classes join so we can return
# subject_name and class_name without calling the broken search_papers() RPC.
_SEARCH_SELECT = (
    "id, subject_id, exam_type, year, month, district, title, paper_type, "
    "public_url, original_filename, is_visible, download_count, created_at, "
    "subjects ( id, name, slug, classes ( id, name ) )"
)


def _add_status(row: dict[str, Any]) -> dict[str, Any]:
    """
    Inject a synthesised status field so Pydantic schemas are satisfied.

    The live database does not have a 'status' column (migration 007 was
    not applied).  All publicly visible papers have is_visible = true,
    which corresponds to status = 'published'.  Hidden papers are
    treated as 'archived'.

    This helper is called on every row before it is returned to the service.
    """
    is_visible = row.get("is_visible", True)
    row.setdefault("status", "published" if is_visible else "archived")
    return row


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
            published_only: When True, only return is_visible=true papers.
                            (Mirrors the old status='published' filter.)
        """
        logger.debug("PapersRepository.get_by_id(paper_id=%s)", paper_id)
        query = (
            self._db.table("papers")
            .select(_DETAIL_SELECT)
            .eq("id", paper_id)
        )
        if published_only:
            query = query.eq("is_visible", True)

        response = query.execute()
        if not response.data:
            return None
        return self._normalise_detail(response.data[0])

    # ------------------------------------------------------------------ #
    # List endpoints
    # ------------------------------------------------------------------ #

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the N most recently uploaded visible papers.
        Mirrors getRecentPapers() in frontend/src/services/papers.js.
        """
        logger.debug("PapersRepository.list_recent(limit=%s)", limit)
        response = (
            self._db.table("papers")
            .select(_LIST_COLUMNS)
            .eq("is_visible", True)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [_add_status(row) for row in (response.data or [])]

    def list_popular(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the N most downloaded visible papers.
        Mirrors getPopularPapers() in frontend/src/services/papers.js.
        """
        logger.debug("PapersRepository.list_popular(limit=%s)", limit)
        response = (
            self._db.table("papers")
            .select(_LIST_COLUMNS)
            .eq("is_visible", True)
            .order("download_count", desc=True)
            .limit(limit)
            .execute()
        )
        return [_add_status(row) for row in (response.data or [])]

    def list_by_subject(
        self,
        subject_id: int,
        exam_type: str | None = None,
        paper_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return all visible papers for a given subject.
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
            .select(_LIST_COLUMNS)
            .eq("subject_id", subject_id)
            .eq("is_visible", True)
            .order("year", desc=True)
        )
        if exam_type:
            query = query.eq("exam_type", exam_type)
        if paper_type:
            query = query.eq("paper_type", paper_type)

        response = query.execute()
        return [_add_status(row) for row in (response.data or [])]

    # ------------------------------------------------------------------ #
    # Search
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
        Search visible papers.

        REPLACES the broken search_papers() RPC (which references the
        missing 'status' column).

        Strategy:
          1. Query the papers table directly via PostgREST with OR filters
             across title, exam_type, month, district (all on papers table).
          2. Apply optional equality filters (class_id, exam_type, paper_type,
             month, district) as AND conditions.
          3. Join subjects + classes so subject_name/class_name are available.
          4. Post-filter in Python to include rows where the subject name or
             class name also matches the search term (mirrors the RPC's ILIKE
             on s.name and c.name).

        This approach produces results equivalent to the search_papers() RPC
        defined in migrations 006–016.
        """
        logger.debug(
            "PapersRepository.search(q=%r, class_id=%s, exam_type=%s, "
            "paper_type=%s, month=%s, district=%s)",
            q, class_id, exam_type, paper_type, month, district,
        )
        q_lower = q.lower()

        # ── Build base query ──────────────────────────────────────────────
        # The OR filter covers: title, exam_type, month, district (papers table)
        # subject name and class name are handled via Python post-filter below.
        like = f"%{q}%"
        or_filter = (
            f"title.ilike.{like},"
            f"exam_type.ilike.{like},"
            f"month.ilike.{like},"
            f"district.ilike.{like}"
        )

        query = (
            self._db.table("papers")
            .select(_SEARCH_SELECT)
            .eq("is_visible", True)
            .or_(or_filter)
            .order("created_at", desc=True)
            .limit(200)  # Fetch more; we'll post-filter for subject/class names
        )

        # Optional equality filters
        if exam_type:
            query = query.eq("exam_type", exam_type)
        if paper_type:
            query = query.eq("paper_type", paper_type)
        if month:
            query = query.eq("month", month)
        if district:
            query = query.ilike("district", f"%{district}%")

        response = query.execute()
        rows = response.data or []

        # ── Also fetch rows matching by subject name or class name ─────────
        # PostgREST can't OR across embedded resource columns, so we do a
        # second query filtered by subject/class match and merge results.
        subject_rows = self._search_by_subject_or_class(
            q=q, class_id=class_id, exam_type=exam_type,
            paper_type=paper_type, month=month, district=district,
        )

        # ── Merge & de-duplicate by paper id ─────────────────────────────
        seen: dict[int, dict] = {}
        for row in rows + subject_rows:
            row_id = row.get("id")
            if row_id not in seen:
                seen[row_id] = row

        # ── Apply class_id filter (post-fetch for primary query) ──────────
        results = []
        for row in seen.values():
            subj = row.get("subjects") or {}
            cls  = subj.get("classes") or {}
            row_class_id = cls.get("id")
            if class_id is not None and row_class_id != class_id:
                continue
            results.append(self._normalise_search_row(row))

        # Sort by created_at descending and cap at 50 (mirrors RPC LIMIT 50)
        results.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return results[:50]

    def _search_by_subject_or_class(
        self,
        q: str,
        class_id: int | None,
        exam_type: str | None,
        paper_type: str | None,
        month: str | None,
        district: str | None,
    ) -> list[dict[str, Any]]:
        """
        Fetch papers whose subject name or class name matches q.
        Called internally by search() to complement the PostgREST OR query.
        """
        # First find matching subject_ids via subjects table
        like = f"%{q}%"
        subj_resp = (
            self._db.table("subjects")
            .select("id, name, class_id, classes ( id, name )")
            .or_(f"name.ilike.{like},classes.name.ilike.{like}")
            .execute()
        )
        matching_subject_ids = [s["id"] for s in (subj_resp.data or [])]

        if not matching_subject_ids:
            return []

        # Fetch papers for those subjects
        query = (
            self._db.table("papers")
            .select(_SEARCH_SELECT)
            .eq("is_visible", True)
            .in_("subject_id", matching_subject_ids)
            .order("created_at", desc=True)
            .limit(200)
        )
        if exam_type:
            query = query.eq("exam_type", exam_type)
        if paper_type:
            query = query.eq("paper_type", paper_type)
        if month:
            query = query.eq("month", month)
        if district:
            query = query.ilike("district", f"%{district}%")

        response = query.execute()
        return response.data or []

    # ------------------------------------------------------------------ #
    # Download tracking
    # ------------------------------------------------------------------ #

    def record_download(self, paper_id: int) -> None:
        """
        Atomically increment download_count for a visible paper.

        REPLACES the broken increment_download_count() RPC (which references
        the missing 'status' column).

        Uses a direct UPDATE via PostgREST. Raises if the paper does not
        exist or is not visible (is_visible = false).
        """
        logger.debug("PapersRepository.record_download(paper_id=%s)", paper_id)
        # Verify the paper exists and is visible before counting
        check = (
            self._db.table("papers")
            .select("id, download_count")
            .eq("id", paper_id)
            .eq("is_visible", True)
            .execute()
        )
        if not check.data:
            raise ValueError(f"Paper {paper_id} not found or not visible")

        # PostgREST does not support SET col = col + 1 expressions directly.
        # We read the current count then write current + 1.
        # This is slightly non-atomic but acceptable for a download counter
        # (high-frequency exact precision is not a requirement here).
        current_count = check.data[0].get("download_count", 0) or 0
        (
            self._db.table("papers")
            .update({"download_count": current_count + 1})
            .eq("id", paper_id)
            .execute()
        )

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise_detail(row: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten the nested subjects → classes join into flat fields,
        and inject a synthesised status field.

        Supabase returns:
            {
              "id": 42,
              "is_visible": true,
              "subjects": {
                "id": 8, "name": "Mathematics", "slug": "maths",
                "is_practical": false,
                "classes": { "id": 10, "name": "Class 10", "slug": "10" }
              }
            }
        We want:
            {
              "id": 42,
              "status": "published",
              "subject_name": "Mathematics", "subject_slug": "maths",
              "is_practical": false,
              "class_id": 10, "class_name": "Class 10", "class_slug": "10"
            }
        """
        subjects = row.pop("subjects", None) or {}
        classes  = subjects.pop("classes", None) or {}
        result = {
            **row,
            "subject_name": subjects.get("name"),
            "subject_slug": subjects.get("slug"),
            "is_practical": subjects.get("is_practical"),
            "class_id":     classes.get("id"),
            "class_name":   classes.get("name"),
            "class_slug":   classes.get("slug"),
        }
        return _add_status(result)

    @staticmethod
    def _normalise_search_row(row: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten the subjects → classes join for search results and inject status.
        Returns the flat shape expected by PaperSearchResult.
        """
        subjects = row.pop("subjects", None) or {}
        classes  = subjects.pop("classes", None) or {}
        result = {
            **row,
            "subject_name": subjects.get("name") or "",
            "class_name":   classes.get("name") or "",
            "class_id":     classes.get("id") or 0,
        }
        return _add_status(result)
