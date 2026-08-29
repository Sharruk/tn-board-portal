"""
Community service — business logic for discussions, threaded comments,
paper requests, moderation reports, and user profiles.
"""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.repositories.community_repository import CommunityRepository
from app.schemas.community import (
    CommentCreate,
    CommentOut,
    PaperRequestCreate,
    PaperRequestListResponse,
    PaperRequestOut,
    PostCreate,
    PostListItem,
    PostListResponse,
    PostOut,
    PostUpdate,
    ReportCreate,
    UserProfileOut,
)
from app.utils.exceptions import ForbiddenError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


def build_threaded_comments(flat_comments: list[dict[str, Any]]) -> list[CommentOut]:
    """Turn flat comments list into threaded tree structure with nested replies."""
    comment_map: dict[str, CommentOut] = {}
    root_comments: list[CommentOut] = []

    for c in flat_comments:
        c_out = CommentOut(
            id=str(c["id"]),
            post_id=str(c["post_id"]),
            firebase_uid=c.get("firebase_uid"),
            author_name=c["author_name"],
            author_avatar=c.get("author_avatar"),
            parent_id=str(c["parent_id"]) if c.get("parent_id") else None,
            content=c["content"],
            created_at=c["created_at"],
            replies=[],
        )
        comment_map[str(c["id"])] = c_out

    for c in flat_comments:
        c_id = str(c["id"])
        parent_id = str(c["parent_id"]) if c.get("parent_id") else None
        if parent_id and parent_id in comment_map:
            comment_map[parent_id].replies.append(comment_map[c_id])
        else:
            root_comments.append(comment_map[c_id])

    return root_comments


class CommunityService:
    """Service layer for community forum."""

    def __init__(self, db: Session) -> None:
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
            category=req.category or "Discussion",
            author_avatar=req.author_avatar,
        )

        return PostOut(
            id=str(post["id"]),
            title=post["title"],
            content=post["content"],
            category=post.get("category", "Discussion"),
            status=post.get("status", "open"),
            author_name=post["author_name"],
            author_avatar=post.get("author_avatar"),
            firebase_uid=post.get("firebase_uid"),
            upvotes=post.get("upvotes", 0),
            likes_count=post.get("likes_count", 0),
            reply_count=0,
            comments_count=0,
            is_pinned=post.get("is_pinned", False),
            created_at=post["created_at"],
            updated_at=post.get("updated_at"),
            comments=[],
        )

    def list_posts(
        self,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> PostListResponse:
        """List active discussion posts with reply counts and category filter."""
        page = max(1, page)
        page_size = min(50, max(1, page_size))

        posts, total = self._repo.list_posts(
            category=category,
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
        )
        post_ids = [str(p["id"]) for p in posts]
        comment_counts = self._repo.count_comments_for_posts(post_ids)

        items = [
            PostListItem(
                id=str(p["id"]),
                title=p["title"],
                content=p["content"][:200] + ("..." if len(p["content"]) > 200 else ""),
                category=p.get("category", "Discussion"),
                status=p.get("status", "open"),
                author_name=p["author_name"],
                author_avatar=p.get("author_avatar"),
                firebase_uid=p.get("firebase_uid"),
                upvotes=p.get("upvotes", 0),
                likes_count=p.get("likes_count", 0),
                reply_count=comment_counts.get(str(p["id"]), p.get("comments_count", 0)),
                comments_count=comment_counts.get(str(p["id"]), p.get("comments_count", 0)),
                is_pinned=p.get("is_pinned", False),
                created_at=p["created_at"],
                updated_at=p.get("updated_at"),
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

    def get_post(self, post_id: str, allow_deleted: bool = False) -> PostOut:
        """Retrieve a single post along with its threaded comments."""
        post = self._repo.get_post_by_id(post_id, allow_deleted=allow_deleted)
        if not post:
            raise NotFoundError(resource="Post", identifier=post_id)

        comment_rows = self._repo.get_comments_for_post(post_id, allow_deleted=allow_deleted)
        threaded_comments = build_threaded_comments(comment_rows)

        return PostOut(
            id=str(post["id"]),
            title=post["title"],
            content=post["content"],
            category=post.get("category", "Discussion"),
            status=post.get("status", "open"),
            author_name=post["author_name"],
            author_avatar=post.get("author_avatar"),
            firebase_uid=post.get("firebase_uid"),
            upvotes=post.get("upvotes", 0),
            likes_count=post.get("likes_count", 0),
            reply_count=len(comment_rows),
            comments_count=len(comment_rows),
            is_pinned=post.get("is_pinned", False),
            created_at=post["created_at"],
            updated_at=post.get("updated_at"),
            comments=threaded_comments,
        )

    def update_post(
        self,
        post_id: str,
        req: PostUpdate,
        current_user: dict[str, Any],
    ) -> PostOut:
        """Update a post (author or admin only)."""
        post = self._repo.get_post_by_id(post_id)
        if not post:
            raise NotFoundError(resource="Post", identifier=post_id)

        is_admin = current_user.get("role") == "ADMIN"
        is_owner = current_user.get("firebase_uid") == post.get("firebase_uid")
        if not (is_admin or is_owner):
            raise ForbiddenError("You can only edit your own posts.")

        upd = self._repo.update_post(
            post_id=post_id,
            title=req.title.strip() if req.title else None,
            content=req.content.strip() if req.content else None,
            category=req.category,
            status=req.status,
        )
        return self.get_post(post_id)

    def delete_post(
        self,
        post_id: str,
        current_user: dict[str, Any],
        hard_delete: bool = False,
    ) -> dict[str, Any]:
        """Delete a post (author or admin)."""
        post = self._repo.get_post_by_id(post_id, allow_deleted=True)
        if not post:
            raise NotFoundError(resource="Post", identifier=post_id)

        is_admin = current_user.get("role") == "ADMIN"
        is_owner = current_user.get("firebase_uid") == post.get("firebase_uid")
        if not (is_admin or is_owner):
            raise ForbiddenError("You can only delete your own posts.")

        self._repo.delete_post(post_id, hard_delete=hard_delete and is_admin)
        return {"success": True, "message": "Post deleted"}

    def add_comment(
        self,
        post_id: str,
        req: CommentCreate,
        firebase_uid: str,
        author_name: str | None = None,
    ) -> CommentOut:
        """Add a comment or reply to an existing post."""
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
            parent_id=req.parent_id,
            author_avatar=req.author_avatar,
        )

        return CommentOut(
            id=str(row["id"]),
            post_id=str(row["post_id"]),
            firebase_uid=row.get("firebase_uid"),
            author_name=row["author_name"],
            author_avatar=row.get("author_avatar"),
            parent_id=row.get("parent_id"),
            content=row["content"],
            created_at=row["created_at"],
            replies=[],
        )

    def delete_comment(
        self,
        comment_id: str,
        current_user: dict[str, Any],
        hard_delete: bool = False,
    ) -> dict[str, Any]:
        """Delete a comment (author or admin)."""
        is_admin = current_user.get("role") == "ADMIN"
        self._repo.delete_comment(comment_id, hard_delete=hard_delete and is_admin)
        return {"success": True, "message": "Comment deleted"}

    def toggle_upvote(self, post_id: str, firebase_uid: str) -> dict[str, Any]:
        """Toggle an upvote/like on a post."""
        post = self._repo.get_post_by_id(post_id)
        if not post:
            raise NotFoundError(resource="Post", identifier=post_id)

        return self._repo.toggle_upvote(post_id, firebase_uid)

    # ── Moderation & Reports ──────────────────────────────────────────────────

    def create_report(self, req: ReportCreate, reporter_uid: str) -> dict[str, Any]:
        """File a report against inappropriate content."""
        if not req.reason.strip():
            raise ValidationError("Report reason is required.")
        return self._repo.create_report(
            reporter_uid=reporter_uid,
            target_type=req.target_type,
            target_id=req.target_id,
            reason=req.reason.strip(),
        )

    def list_reports(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List content reports for admin review."""
        return self._repo.list_reports(status=status)

    def update_report_status(self, report_id: str, status: str) -> dict[str, Any]:
        """Update report status."""
        success = self._repo.update_report_status(report_id, status)
        return {"success": success}

    # ── Paper Requests ────────────────────────────────────────────────────────

    def create_paper_request(
        self,
        req: PaperRequestCreate,
        firebase_uid: str,
        author_name: str | None = None,
    ) -> PaperRequestOut:
        """Create a paper request."""
        display_name = (author_name or "").strip() or "Student"
        row = self._repo.create_paper_request(
            firebase_uid=firebase_uid,
            author_name=display_name,
            title=req.title.strip(),
            exam_type=req.exam_type.strip(),
            year=req.year,
            month=req.month,
            district=req.district,
            description=req.description,
            class_id=req.class_id,
            subject_id=req.subject_id,
            author_avatar=req.author_avatar,
        )
        return PaperRequestOut(**row)

    def list_paper_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaperRequestListResponse:
        """List community paper requests with pagination."""
        page = max(1, page)
        page_size = min(50, max(1, page_size))
        requests, total = self._repo.list_paper_requests(status=status, page=page, page_size=page_size)
        return PaperRequestListResponse(
            data=[PaperRequestOut(**r) for r in requests],
            total=total,
            page=page,
            page_size=page_size,
        )

    def update_paper_request(
        self,
        request_id: str,
        status: Optional[str] = None,
        fulfilled_paper_id: Optional[int] = None,
    ) -> PaperRequestOut:
        """Admin or author updates paper request status."""
        row = self._repo.update_paper_request(
            request_id=request_id,
            status=status,
            fulfilled_paper_id=fulfilled_paper_id,
        )
        return PaperRequestOut(**row)

    # ── User Profile ──────────────────────────────────────────────────────────

    def get_user_profile(self, uid: str) -> UserProfileOut:
        """Retrieve sanitized public profile."""
        profile = self._repo.get_user_profile(uid)
        return UserProfileOut(**profile)
