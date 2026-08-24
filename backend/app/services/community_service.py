"""
Community service — business logic for discussions and comments.
"""

import logging
from typing import Any

from supabase import Client

from app.repositories.community_repository import CommunityRepository
from app.schemas.community import (
    CommentCreate,
    CommentOut,
    PostCreate,
    PostListItem,
    PostListResponse,
    PostOut,
)
from app.utils.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class CommunityService:
    """Service layer for community forum."""

    def __init__(self, db: Client) -> None:
        self._repo = CommunityRepository(db)

    def create_post(
        self,
        req: PostCreate,
        firebase_uid: str,
        author_name: str | None = None,
    ) -> PostOut:
        """Create a new community discussion post."""
        title = req.title.strip()
        content = req.content.strip()

        if len(title) < 3:
            raise ValidationError("Title must be at least 3 characters long.")
        if len(content) < 3:
            raise ValidationError("Content must be at least 3 characters long.")

        display_name = (author_name or "").strip() or "Student"

        post = self._repo.create_post(
            firebase_uid=firebase_uid,
            author_name=display_name,
            title=title,
            content=content,
        )

        return PostOut(
            id=str(post["id"]),
            title=post["title"],
            content=post["content"],
            author_name=post["author_name"],
            upvotes=post.get("upvotes", 0),
            reply_count=0,
            is_pinned=post.get("is_pinned", False),
            created_at=post["created_at"],
            comments=[],
        )

    def list_posts(self, page: int = 1, page_size: int = 20) -> PostListResponse:
        """List active discussion posts with reply counts."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50:
            page_size = 20

        posts, total = self._repo.list_posts(page=page, page_size=page_size)
        post_ids = [str(p["id"]) for p in posts]
        comment_counts = self._repo.count_comments_for_posts(post_ids)

        items = [
            PostListItem(
                id=str(p["id"]),
                title=p["title"],
                content=p["content"][:200] + ("..." if len(p["content"]) > 200 else ""),
                author_name=p["author_name"],
                upvotes=p.get("upvotes", 0),
                reply_count=comment_counts.get(str(p["id"]), 0),
                is_pinned=p.get("is_pinned", False),
                created_at=p["created_at"],
            )
            for p in posts
        ]

        has_next = (page * page_size) < total

        return PostListResponse(
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        )

    def get_post(self, post_id: str) -> PostOut:
        """Retrieve a single post along with its comments."""
        post = self._repo.get_post_by_id(post_id)
        if not post:
            raise NotFoundError(resource="Post", identifier=post_id)

        comment_rows = self._repo.get_comments_for_post(post_id)
        comments = [
            CommentOut(
                id=str(c["id"]),
                post_id=str(c["post_id"]),
                author_name=c["author_name"],
                content=c["content"],
                created_at=c["created_at"],
            )
            for c in comment_rows
        ]

        return PostOut(
            id=str(post["id"]),
            title=post["title"],
            content=post["content"],
            author_name=post["author_name"],
            upvotes=post.get("upvotes", 0),
            reply_count=len(comments),
            is_pinned=post.get("is_pinned", False),
            created_at=post["created_at"],
            comments=comments,
        )

    def add_comment(
        self,
        post_id: str,
        req: CommentCreate,
        firebase_uid: str,
        author_name: str | None = None,
    ) -> CommentOut:
        """Add a comment/reply to an existing post."""
        post = self._repo.get_post_by_id(post_id)
        if not post:
            raise NotFoundError(resource="Post", identifier=post_id)

        content = req.content.strip()
        if not content:
            raise ValidationError("Comment cannot be empty.")

        display_name = (author_name or "").strip() or "Student"

        row = self._repo.create_comment(
            post_id=post_id,
            firebase_uid=firebase_uid,
            author_name=display_name,
            content=content,
        )

        return CommentOut(
            id=str(row["id"]),
            post_id=str(row["post_id"]),
            author_name=row["author_name"],
            content=row["content"],
            created_at=row["created_at"],
        )

    def toggle_upvote(self, post_id: str, firebase_uid: str) -> dict[str, Any]:
        """Toggle an upvote on a post."""
        post = self._repo.get_post_by_id(post_id)
        if not post:
            raise NotFoundError(resource="Post", identifier=post_id)

        return self._repo.toggle_upvote(post_id, firebase_uid)
