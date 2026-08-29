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
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user, get_current_user_optional, require_role
from app.dependencies.supabase import get_db
from app.schemas.paper import (
    PaperCommentCreate,
    PaperCommentOut,
    PaperDetail,
    PaperLikeResponse,
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
    db: Session = Depends(get_db),
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
        "Full-text paper search.\n\n"
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
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search published papers using direct SQL search."""
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    current_user: dict = Depends(require_role(["USER", "CONTRIBUTOR", "ADMIN", "SUPER_ADMIN"])),
    db: Session = Depends(get_db),
) -> None:
    """Increment download counter for a published paper."""
    service = PapersService(db)
    service.record_download(
        paper_id,
        user_id=current_user.get("firebase_uid"),
        user_email=current_user.get("email"),
    )


# ── Paper Likes & Comments Endpoints ──────────────────────────────────────────

@router.post(
    "/{paper_id}/like",
    response_model=PaperLikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle like on a paper",
    description="Authenticated endpoint. Toggles like/unlike for the authenticated Firebase user.",
)
async def toggle_paper_like(
    paper_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperLikeResponse:
    """Toggle like on a paper."""
    service = PapersService(db)
    res = service.toggle_like(paper_id, firebase_uid=current_user["firebase_uid"])
    return PaperLikeResponse(**res)


@router.get(
    "/{paper_id}/likes",
    response_model=PaperLikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paper likes count and user status",
    description="Public endpoint. Returns like count and whether the optional current user liked it.",
)
async def get_paper_likes(
    paper_id: int,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> PaperLikeResponse:
    """Get paper likes status."""
    service = PapersService(db)
    uid = current_user.get("firebase_uid") if current_user else None
    res = service.get_likes_info(paper_id, firebase_uid=uid)
    return PaperLikeResponse(**res)


@router.get(
    "/{paper_id}/comments",
    response_model=list[PaperCommentOut],
    status_code=status.HTTP_200_OK,
    summary="Get paper comments",
    description="Public endpoint. Returns threaded comments for a question paper.",
)
async def get_paper_comments(
    paper_id: int,
    db: Session = Depends(get_db),
) -> list[PaperCommentOut]:
    """Get comments for a paper."""
    service = PapersService(db)
    return service.get_comments(paper_id)


@router.post(
    "/{paper_id}/comments",
    response_model=PaperCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to paper",
    description="Authenticated endpoint. Adds a comment or nested reply to a paper.",
)
async def add_paper_comment(
    paper_id: int,
    req: PaperCommentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperCommentOut:
    """Add a comment on a paper."""
    service = PapersService(db)
    author_name = current_user.get("display_name") or current_user.get("email", "").split("@")[0] or "Student"
    res = service.add_comment(
        paper_id=paper_id,
        content=req.content,
        firebase_uid=current_user["firebase_uid"],
        author_name=author_name,
        parent_id=req.parent_id,
        author_avatar=req.author_avatar,
    )
    return PaperCommentOut(
        id=str(res["id"]),
        paper_id=res["paper_id"],
        firebase_uid=res["firebase_uid"],
        author_name=res["author_name"],
        author_avatar=res.get("author_avatar"),
        parent_id=res.get("parent_id"),
        content=res["content"],
        is_deleted=res.get("is_deleted", False),
        created_at=res["created_at"],
        updated_at=res["updated_at"],
        replies=[],
    )


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete paper comment",
)
async def delete_paper_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a paper comment."""
    service = PapersService(db)
    return service.delete_comment(comment_id=comment_id, current_user=current_user)


