"""
Community discussion, requests, moderation, and member profile endpoints.
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_admin, get_current_user
from app.dependencies.supabase import get_db
from app.schemas.community import (
    CommentCreate,
    CommentOut,
    PaperRequestCreate,
    PaperRequestListResponse,
    PaperRequestOut,
    PostCreate,
    PostListResponse,
    PostOut,
    PostUpdate,
    ReportCreate,
    UserProfileOut,
)
from app.services.community_service import CommunityService

router = APIRouter(prefix="/community", tags=["Community"])


# ── Posts ─────────────────────────────────────────────────────────────────────

@router.get(
    "/posts",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="List community discussion posts",
    description="Public endpoint. Returns paginated discussions sorted with pinned posts first, then newest.",
)
async def list_posts(
    category: Annotated[Optional[str], Query(description="Category filter")] = None,
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Items per page", ge=1, le=50)] = 20,
    db: Session = Depends(get_db),
) -> PostListResponse:
    """List active discussion posts with pagination."""
    service = CommunityService(db)
    return service.list_posts(category=category, page=page, page_size=page_size)


@router.post(
    "/posts",
    response_model=PostOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a discussion post",
    description="Authenticated endpoint. Creates a new community discussion topic.",
)
async def create_post(
    req: PostCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostOut:
    """Create a new post."""
    service = CommunityService(db)
    author_name = current_user.get("display_name") or current_user.get("email", "").split("@")[0] or "Student"
    return service.create_post(
        req=req,
        firebase_uid=current_user["firebase_uid"],
        author_name=author_name,
    )


@router.get(
    "/posts/{post_id}",
    response_model=PostOut,
    status_code=status.HTTP_200_OK,
    summary="Get discussion post with threaded comments",
    description="Public endpoint. Retrieves full post text along with all active threaded comments.",
)
async def get_post(
    post_id: str,
    db: Session = Depends(get_db),
) -> PostOut:
    """Get post and comment thread."""
    service = CommunityService(db)
    return service.get_post(post_id)


@router.patch(
    "/posts/{post_id}",
    response_model=PostOut,
    status_code=status.HTTP_200_OK,
    summary="Update a discussion post",
    description="Authenticated endpoint (author or admin).",
)
async def update_post(
    post_id: str,
    req: PostUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PostOut:
    """Edit post title, content, category, or status."""
    service = CommunityService(db)
    return service.update_post(post_id=post_id, req=req, current_user=current_user)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a discussion post",
    description="Authenticated endpoint (author or admin).",
)
async def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a post."""
    service = CommunityService(db)
    return service.delete_post(post_id=post_id, current_user=current_user)


# ── Comments & Votes ──────────────────────────────────────────────────────────

@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Reply/comment on a discussion post",
    description="Authenticated endpoint. Adds a comment or nested reply to a discussion thread.",
)
async def add_comment(
    post_id: str,
    req: CommentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentOut:
    """Add a comment/reply to a post."""
    service = CommunityService(db)
    author_name = current_user.get("display_name") or current_user.get("email", "").split("@")[0] or "Student"
    return service.add_comment(
        post_id=post_id,
        req=req,
        firebase_uid=current_user["firebase_uid"],
        author_name=author_name,
    )


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a comment",
    description="Authenticated endpoint (author or admin).",
)
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete comment."""
    service = CommunityService(db)
    return service.delete_comment(comment_id=comment_id, current_user=current_user)


@router.post(
    "/posts/{post_id}/upvote",
    status_code=status.HTTP_200_OK,
    summary="Toggle upvote / like on a post",
    description="Authenticated endpoint. Toggles like on a post for the current user.",
)
async def toggle_upvote(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Toggle upvote/like."""
    service = CommunityService(db)
    return service.toggle_upvote(
        post_id=post_id,
        firebase_uid=current_user["firebase_uid"],
    )


# ── Reports ───────────────────────────────────────────────────────────────────

@router.post(
    "/reports",
    status_code=status.HTTP_201_CREATED,
    summary="Report inappropriate content",
    description="Authenticated endpoint. Submits a content report for admin moderation.",
)
async def create_report(
    req: ReportCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Submit a moderation report."""
    service = CommunityService(db)
    return service.create_report(req=req, reporter_uid=current_user["firebase_uid"])


@router.get(
    "/reports",
    status_code=status.HTTP_200_OK,
    summary="List moderation reports (Admin only)",
)
async def list_reports(
    status: Annotated[Optional[str], Query()] = None,
    admin_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List reports for admin."""
    service = CommunityService(db)
    return service.list_reports(status=status)


@router.patch(
    "/reports/{report_id}",
    status_code=status.HTTP_200_OK,
    summary="Update report status (Admin only)",
)
async def update_report(
    report_id: str,
    status: Annotated[str, Query(description="'reviewed', 'dismissed', 'actioned'")],
    admin_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Update report status."""
    service = CommunityService(db)
    return service.update_report_status(report_id=report_id, status=status)


# ── Paper Requests ────────────────────────────────────────────────────────────

@router.get(
    "/requests",
    response_model=PaperRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="List community paper requests",
)
async def list_paper_requests(
    status: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    db: Session = Depends(get_db),
) -> PaperRequestListResponse:
    """List paper requests."""
    service = CommunityService(db)
    return service.list_paper_requests(status=status, page=page, page_size=page_size)


@router.post(
    "/requests",
    response_model=PaperRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a paper request",
)
async def create_paper_request(
    req: PaperRequestCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperRequestOut:
    """Create paper request."""
    service = CommunityService(db)
    author_name = current_user.get("display_name") or current_user.get("email", "").split("@")[0] or "Student"
    return service.create_paper_request(
        req=req,
        firebase_uid=current_user["firebase_uid"],
        author_name=author_name,
    )


@router.patch(
    "/requests/{request_id}",
    response_model=PaperRequestOut,
    status_code=status.HTTP_200_OK,
    summary="Update a paper request (e.g. fulfill or close)",
)
async def update_paper_request(
    request_id: str,
    status: Annotated[Optional[str], Query()] = None,
    fulfilled_paper_id: Annotated[Optional[int], Query()] = None,
    admin_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> PaperRequestOut:
    """Update paper request status."""
    service = CommunityService(db)
    return service.update_paper_request(
        request_id=request_id,
        status=status,
        fulfilled_paper_id=fulfilled_paper_id,
    )


# ── User Public Profile ───────────────────────────────────────────────────────

@router.get(
    "/users/{uid}",
    response_model=UserProfileOut,
    status_code=status.HTTP_200_OK,
    summary="Get sanitized public user profile",
)
async def get_user_profile(
    uid: str,
    db: Session = Depends(get_db),
) -> UserProfileOut:
    """Get public profile for contributor or member."""
    service = CommunityService(db)
    return service.get_user_profile(uid)
