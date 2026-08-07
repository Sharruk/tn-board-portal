"""
Papers endpoints.

Endpoints:
  GET  /api/v1/papers                        — recent or popular list
  GET  /api/v1/papers/search                 — full-text search via RPC
  GET  /api/v1/papers/by-subject/{subject_id} — papers for a subject
  GET  /api/v1/papers/{id}                   — single paper detail
  POST /api/v1/papers/{id}/download          — increment download counter

IMPORTANT — route ordering:
  /search and /by-subject MUST be registered before /{id} in the router.
  FastAPI matches routes in registration order. A literal path segment
  ('search', 'by-subject') would be captured by /{id} if registered first.
  The router.include_router() call in router.py handles this correctly by
  relying on FastAPI's own ordering rules — explicit paths always win over
  path parameters — but we still keep the explicit routes first for clarity.

Route responsibilities:
  - Validate path/query params (FastAPI handles this via type hints)
  - Call the service
  - Return the response model
  - Nothing else

All business logic lives in PapersService.
All database access lives in PapersRepository.
"""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from app.dependencies.supabase import get_db
from app.schemas.paper import (
    PaperListResponse,
    PaperResponse,
    SearchResponse,
)
from app.services.papers_service import DEFAULT_LIMIT, MAX_LIMIT, PapersService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["Papers"])


# ── GET /api/v1/papers ────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaperListResponse,
    summary="List papers",
    description=(
        "Returns published papers ordered by `sort`. "
        "Use `sort=recent` (default) for newest-first, `sort=popular` for most-downloaded.\n\n"
        "Mirrors `getRecentPapers()` and `getPopularPapers()` in "
        "`frontend/src/services/papers.js`."
    ),
)
async def list_papers(
    sort: Annotated[
        Literal["recent", "popular"],
        Query(description="Sort order: 'recent' (newest) or 'popular' (most downloaded)"),
    ] = "recent",
    limit: Annotated[
        int,
        Query(description=f"Number of papers to return (1–{MAX_LIMIT})", ge=1, le=MAX_LIMIT),
    ] = DEFAULT_LIMIT,
    db: Client = Depends(get_db),
) -> PaperListResponse:
    """Return recent or popular published papers."""
    service = PapersService(db)
    return service.list_papers(sort=sort, limit=limit)


# ── GET /api/v1/papers/search ─────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search papers",
    description=(
        "Full-text paper search using the `search_papers()` Supabase RPC.\n\n"
        "Mirrors `searchPapers()` in `frontend/src/services/search.js`, "
        "including term expansion (e.g. 'maths' → 'mathematics').\n\n"
        "All filter parameters are optional. An empty `q` returns zero results."
    ),
    responses={
        200: {"description": "Search results (may be empty)"},
    },
)
async def search_papers(
    q: Annotated[
        str,
        Query(description="Search term (required, but empty string returns zero results)"),
    ] = "",
    class_id: Annotated[
        int | None,
        Query(description="Filter by class id (9, 10, 11, or 12)"),
    ] = None,
    exam_type: Annotated[
        str | None,
        Query(description="Filter by exam type (e.g. 'Annual Exam', 'First Mid Term Test')"),
    ] = None,
    paper_type: Annotated[
        str | None,
        Query(description="Filter by paper type: 'question' or 'answer_key'"),
    ] = None,
    month: Annotated[
        str | None,
        Query(description="Filter by month name (e.g. 'July', 'November')"),
    ] = None,
    district: Annotated[
        str | None,
        Query(description="Filter by district (partial match, e.g. 'Chennai')"),
    ] = None,
    db: Client = Depends(get_db),
) -> SearchResponse:
    """Search published papers using the existing search_papers() RPC."""
    service = PapersService(db)
    return service.search_papers(
        q=q,
        class_id=class_id,
        exam_type=exam_type,
        paper_type=paper_type,
        month=month,
        district=district,
    )


# ── GET /api/v1/papers/by-subject/{subject_id} ────────────────────────────────

@router.get(
    "/by-subject/{subject_id}",
    response_model=PaperListResponse,
    summary="Papers for a subject",
    description=(
        "Returns all published papers for the given subject, ordered by year DESC.\n\n"
        "Mirrors `getPapersForSubject()` in `frontend/src/services/subjects.js`.\n\n"
        "Optional filters: `exam_type`, `paper_type`."
    ),
    responses={
        200: {"description": "Papers list (may be empty)"},
    },
)
async def list_papers_by_subject(
    subject_id: int,
    exam_type: Annotated[
        str | None,
        Query(description="Filter by exam type"),
    ] = None,
    paper_type: Annotated[
        str | None,
        Query(description="Filter by paper type: 'question' or 'answer_key'"),
    ] = None,
    db: Client = Depends(get_db),
) -> PaperListResponse:
    """Return all published papers for a specific subject."""
    service = PapersService(db)
    return service.list_by_subject(
        subject_id=subject_id,
        exam_type=exam_type,
        paper_type=paper_type,
    )


# ── GET /api/v1/papers/{id} ───────────────────────────────────────────────────

@router.get(
    "/{paper_id}",
    response_model=PaperResponse,
    summary="Get a single paper",
    description=(
        "Returns one published paper by id with full subject and class detail.\n\n"
        "Mirrors `getPaper(id)` in `frontend/src/services/papers.js`."
    ),
    responses={
        404: {"description": "Paper not found or not published"},
    },
)
async def get_paper(
    paper_id: int,
    db: Client = Depends(get_db),
) -> PaperResponse:
    """Return a single published paper by its primary key."""
    service = PapersService(db)
    return service.get_paper(paper_id)


# ── POST /api/v1/papers/{id}/download ─────────────────────────────────────────

@router.post(
    "/{paper_id}/download",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record a paper download",
    description=(
        "Atomically increments `download_count` for a published paper.\n\n"
        "Calls the `increment_download_count()` Supabase RPC defined in migration 004/007.\n\n"
        "Mirrors `recordDownload(id)` in `frontend/src/services/papers.js`.\n\n"
        "Returns 204 No Content on success. Returns 404 if the paper "
        "does not exist or is not published."
    ),
    responses={
        204: {"description": "Download recorded"},
        404: {"description": "Paper not found or not published"},
    },
)
async def record_download(
    paper_id: int,
    db: Client = Depends(get_db),
) -> None:
    """Increment download counter for a published paper."""
    service = PapersService(db)
    service.record_download(paper_id)
