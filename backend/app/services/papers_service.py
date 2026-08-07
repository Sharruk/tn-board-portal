"""
Papers service — business logic for the papers domain.

This layer sits between routes and the repository.
All business rules live here so they are testable independently
of HTTP and Supabase.

Business rules implemented:
  - Only published papers are returned to public endpoints
  - Search term expansion: aliases like 'maths' → 'mathematics'
    (mirrors expandTerms() in frontend/src/services/search.js exactly)
  - De-duplication of search results when multiple expanded terms match
  - download tracking delegates to the repository's RPC call
  - limit capped at MAX_LIMIT to prevent abuse
"""

import logging
from typing import Literal

from supabase import Client

from app.repositories.papers_repository import PapersRepository
from app.schemas.paper import (
    PaperListResponse,
    PaperResponse,
    PaperSearchResult,
    PaperSummary,
    SearchResponse,
)
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)

# Maximum rows any list endpoint will return
MAX_LIMIT = 100
DEFAULT_LIMIT = 10

# ── Term expansion ────────────────────────────────────────────────────────────
# Mirrors SUBJECT_ALIASES + EXAM_PATTERNS from frontend/src/services/search.js
# exactly so API search results match what the frontend produces.

_SUBJECT_ALIASES: dict[str, str] = {
    "maths": "mathematics", "math": "mathematics", "mathematics": "mathematics",
    "phy": "physics", "physics": "physics",
    "chem": "chemistry", "chemistry": "chemistry",
    "bio": "biology", "biology": "biology",
    "eng": "english", "english": "english",
    "tamil": "tamil",
    "cs": "computer science", "computer": "computer science",
    "history": "history",
    "geo": "geography", "geography": "geography",
    "civics": "civics",
    "economics": "economics",
    "commerce": "commerce",
    "accounts": "accountancy", "accountancy": "accountancy",
    "social": "social science", "science": "science",
}

_EXAM_PATTERNS: list[str] = [
    "monthly test",
    "first mid term test", "first mid term",
    "unit test 1", "unit test 2", "unit test 3",
    "quarterly exam", "quarterly",
    "half yearly exam", "half yearly",
    "annual exam", "annual",
    "public exam",
    "practical exam",
    "model exam",
]


def _expand_terms(q: str) -> list[str]:
    """
    Expand a search query into a list of related terms.

    Mirrors expandTerms() in frontend/src/services/search.js.
    The original term is always included. Subject aliases and exam
    patterns are added when they match the query.
    """
    normalized = q.strip().lower()
    terms: set[str] = {normalized}

    for alias, full in _SUBJECT_ALIASES.items():
        if alias in normalized and full != normalized:
            terms.add(full)

    for pattern in _EXAM_PATTERNS:
        if pattern in normalized and pattern != normalized:
            terms.add(pattern)

    return list(terms)


# ── Service ───────────────────────────────────────────────────────────────────

class PapersService:
    """Business logic for the papers domain."""

    def __init__(self, db: Client) -> None:
        self._repo = PapersRepository(db)

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers/{id}
    # ------------------------------------------------------------------ #

    def get_paper(self, paper_id: int) -> PaperResponse:
        """
        Return one published paper with full subject + class detail.
        Raises NotFoundError if not found or not published.
        """
        logger.info("PapersService.get_paper(paper_id=%s)", paper_id)
        row = self._repo.get_by_id(paper_id, published_only=True)
        if row is None:
            raise NotFoundError(resource="Paper", identifier=paper_id)
        return PaperResponse(**row)

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers — list (recent or popular)
    # ------------------------------------------------------------------ #

    def list_papers(
        self,
        sort: Literal["recent", "popular"] = "recent",
        limit: int = DEFAULT_LIMIT,
    ) -> PaperListResponse:
        """
        Return recent or popular published papers.

        Args:
            sort:  'recent'  → ordered by created_at DESC (default)
                   'popular' → ordered by download_count DESC
            limit: Number of papers to return (capped at MAX_LIMIT).
        """
        logger.info("PapersService.list_papers(sort=%s, limit=%s)", sort, limit)
        limit = min(max(1, limit), MAX_LIMIT)

        if sort == "popular":
            rows = self._repo.list_popular(limit)
        else:
            rows = self._repo.list_recent(limit)

        items = [PaperSummary(**row) for row in rows]
        return PaperListResponse(data=items, count=len(items), limit=limit)

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers/by-subject/{subject_id}
    # ------------------------------------------------------------------ #

    def list_by_subject(
        self,
        subject_id: int,
        exam_type: str | None = None,
        paper_type: str | None = None,
    ) -> PaperListResponse:
        """
        Return all published papers for a subject, ordered by year DESC.
        Mirrors getPapersForSubject() in frontend/src/services/subjects.js.
        """
        logger.info(
            "PapersService.list_by_subject(subject_id=%s, exam_type=%s, paper_type=%s)",
            subject_id, exam_type, paper_type,
        )
        rows = self._repo.list_by_subject(
            subject_id=subject_id,
            exam_type=exam_type,
            paper_type=paper_type,
        )
        items = [PaperSummary(**row) for row in rows]
        return PaperListResponse(data=items, count=len(items), limit=len(items))

    # ------------------------------------------------------------------ #
    # GET /api/v1/papers/search
    # ------------------------------------------------------------------ #

    def search_papers(
        self,
        q: str,
        class_id: int | None = None,
        exam_type: str | None = None,
        paper_type: str | None = None,
        month: str | None = None,
        district: str | None = None,
    ) -> SearchResponse:
        """
        Full-text paper search using the search_papers() Supabase RPC.

        Mirrors the frontend searchPapers() function in search.js:
          1. Normalise the raw query
          2. Expand into multiple terms (aliases + exam patterns)
          3. Call search_papers() RPC for each term
          4. De-duplicate results by paper id (last-write-wins)
          5. Return wrapped SearchResponse

        The RPC already filters to status='published'.
        No SQL is written here — we call the existing RPC.
        """
        logger.info(
            "PapersService.search_papers(q=%r, class_id=%s, exam_type=%s, "
            "paper_type=%s, month=%s, district=%s)",
            q, class_id, exam_type, paper_type, month, district,
        )

        raw_query = q.strip()
        if not raw_query:
            return SearchResponse(query="", total=0, results=[])

        terms = _expand_terms(raw_query)
        seen: dict[int, dict] = {}

        for term in terms:
            rows = self._repo.search(
                q=term,
                class_id=class_id,
                exam_type=exam_type,
                paper_type=paper_type,
                month=month,
                district=district,
            )
            for row in rows:
                seen[row["id"]] = row

        results = [PaperSearchResult(**row) for row in seen.values()]
        return SearchResponse(query=raw_query, total=len(results), results=results)

    # ------------------------------------------------------------------ #
    # POST /api/v1/papers/{id}/download
    # ------------------------------------------------------------------ #

    def record_download(self, paper_id: int) -> None:
        """
        Increment the download counter for a published paper.
        Delegates to increment_download_count() RPC.

        Raises NotFoundError if the paper doesn't exist or isn't published
        (the RPC itself raises a Postgres exception — we re-raise as 404).
        """
        logger.info("PapersService.record_download(paper_id=%s)", paper_id)
        try:
            self._repo.record_download(paper_id)
        except Exception as exc:
            # Supabase raises when paper_id is not found or not published
            logger.warning("record_download failed for paper_id=%s: %s", paper_id, exc)
            raise NotFoundError(resource="Paper", identifier=paper_id) from exc
