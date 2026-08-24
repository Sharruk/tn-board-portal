"""
Community discussion endpoints.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from app.db.supabase_client import get_supabase_admin_client
from app.dependencies.auth import get_current_user
from app.schemas.community import (
    CommentCreate,
    CommentOut,
    PostCreate,
    PostListResponse,
    PostOut,
)
from app.services.community_service import CommunityService

router = APIRouter(prefix="/community", tags=["Community"])


@router.get(
    "/posts",
    response_model=PostListResponse,
    status_code=status.HTTP_200_OK,
    summary="List community discussion posts",
    description="Public endpoint. Returns paginated discussions sorted with pinned posts first, then newest.",
)
async def list_posts(
    page: Annotated[int, Query(description="Page number", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Items per page", ge=1, le=50)] = 20,
    db: Client = Depends(get_supabase_admin_client),
) -> PostListResponse:
    """List active discussion posts with pagination."""
    service = CommunityService(db)
    return service.list_posts(page=page, page_size=page_size)


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
    db: Client = Depends(get_supabase_admin_client),
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
    summary="Get discussion post with comments",
    description="Public endpoint. Retrieves full post text along with all active comments.",
)
async def get_post(
    post_id: str,
    db: Client = Depends(get_supabase_admin_client),
) -> PostOut:
    """Get post and comment thread."""
    service = CommunityService(db)
    return service.get_post(post_id)


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Reply/comment on a discussion post",
    description="Authenticated endpoint. Adds a comment to a discussion thread.",
)
async def add_comment(
    post_id: str,
    req: CommentCreate,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_admin_client),
) -> CommentOut:
    """Add a comment to a post."""
    service = CommunityService(db)
    author_name = current_user.get("display_name") or current_user.get("email", "").split("@")[0] or "Student"
    return service.add_comment(
        post_id=post_id,
        req=req,
        firebase_uid=current_user["firebase_uid"],
        author_name=author_name,
    )


@router.post(
    "/posts/{post_id}/upvote",
    status_code=status.HTTP_200_OK,
    summary="Toggle upvote on a post",
    description="Authenticated endpoint. Toggles upvote on a post for the current user.",
)
async def toggle_upvote(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_supabase_admin_client),
) -> dict:
    """Toggle upvote."""
    service = CommunityService(db)
    return service.toggle_upvote(
        post_id=post_id,
        firebase_uid=current_user["firebase_uid"],
    )
