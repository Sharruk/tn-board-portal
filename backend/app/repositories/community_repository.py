"""
Community repository — Supabase data access for community posts, comments, and votes.
"""

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)


class CommunityRepository:
    """Data access layer for community forum."""

    def __init__(self, db: Client) -> None:
        self._db = db

    def create_post(
        self,
        firebase_uid: str,
        author_name: str,
        title: str,
        content: str,
    ) -> dict[str, Any]:
        """Insert a new community discussion post."""
        response = (
            self._db.table("community_posts")
            .insert(
                {
                    "firebase_uid": firebase_uid,
                    "author_name": author_name,
                    "title": title,
                    "content": content,
                    "upvotes": 0,
                    "is_deleted": False,
                }
            )
            .execute()
        )
        if not response.data:
            raise RuntimeError("Failed to create community post")
        return response.data[0]

    def list_posts(self, page: int = 1, page_size: int = 20) -> tuple[list[dict[str, Any]], int]:
        """
        List active community posts with pagination.
        Returns (posts, total_count).
        """
        offset = (page - 1) * page_size
        query = (
            self._db.table("community_posts")
            .select("id,author_name,title,content,upvotes,is_pinned,created_at", count="exact")
            .eq("is_deleted", False)
            .order("is_pinned", desc=True)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
        )
        response = query.execute()
        posts = response.data or []
        total = response.count if response.count is not None else len(posts)
        return posts, total

    def count_comments_for_posts(self, post_ids: list[str]) -> dict[str, int]:
        """Return comment count map {post_id: count} for a list of post IDs."""
        if not post_ids:
            return {}

        response = (
            self._db.table("community_comments")
            .select("post_id")
            .in_("post_id", post_ids)
            .eq("is_deleted", False)
            .execute()
        )
        counts: dict[str, int] = {}
        for row in (response.data or []):
            pid = str(row["post_id"])
            counts[pid] = counts.get(pid, 0) + 1
        return counts

    def get_post_by_id(self, post_id: str) -> dict[str, Any] | None:
        """Fetch a single post by UUID."""
        response = (
            self._db.table("community_posts")
            .select("id,author_name,title,content,upvotes,is_pinned,created_at,is_deleted")
            .eq("id", post_id)
            .execute()
        )
        if not response.data or response.data[0].get("is_deleted"):
            return None
        return response.data[0]

    def get_comments_for_post(self, post_id: str) -> list[dict[str, Any]]:
        """Fetch all active comments for a given post."""
        response = (
            self._db.table("community_comments")
            .select("id,post_id,author_name,content,created_at")
            .eq("post_id", post_id)
            .eq("is_deleted", False)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    def create_comment(
        self,
        post_id: str,
        firebase_uid: str,
        author_name: str,
        content: str,
    ) -> dict[str, Any]:
        """Insert a new comment on a community post."""
        response = (
            self._db.table("community_comments")
            .insert(
                {
                    "post_id": post_id,
                    "firebase_uid": firebase_uid,
                    "author_name": author_name,
                    "content": content,
                    "is_deleted": False,
                }
            )
            .execute()
        )
        if not response.data:
            raise RuntimeError("Failed to create community comment")
        return response.data[0]

    def toggle_upvote(self, post_id: str, firebase_uid: str) -> dict[str, Any]:
        """
        Toggle upvote for a user on a post.
        If already voted, remove vote and decrement.
        If not voted, insert vote and increment.
        """
        vote_check = (
            self._db.table("community_post_votes")
            .select("id")
            .eq("post_id", post_id)
            .eq("firebase_uid", firebase_uid)
            .execute()
        )
        has_voted = bool(vote_check.data)

        # Get current post upvotes
        post = self.get_post_by_id(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        current_upvotes = post.get("upvotes", 0)

        if has_voted:
            self._db.table("community_post_votes").delete().eq("post_id", post_id).eq("firebase_uid", firebase_uid).execute()
            new_upvotes = max(0, current_upvotes - 1)
            voted = False
        else:
            self._db.table("community_post_votes").insert({"post_id": post_id, "firebase_uid": firebase_uid}).execute()
            new_upvotes = current_upvotes + 1
            voted = True

        self._db.table("community_posts").update({"upvotes": new_upvotes}).eq("id", post_id).execute()
        return {"upvotes": new_upvotes, "voted": voted}
