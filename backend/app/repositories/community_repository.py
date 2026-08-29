"""
Community repository — direct PostgreSQL data access for community posts, comments,
paper requests, moderation reports, and user profiles.

Uses SQLAlchemy Session with parameterized SQL.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CommunityRepository:
    """Data access layer for community forum, requests, and moderation."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Posts ─────────────────────────────────────────────────────────────────

    def create_post(
        self,
        firebase_uid: str,
        author_name: str,
        title: str,
        content: str,
        category: str = "Discussion",
        author_avatar: Optional[str] = None,
    ) -> dict[str, Any]:
        """Insert a new community discussion post."""
        stmt = text(
            """
            INSERT INTO community_posts (
                firebase_uid, author_name, author_avatar, title, content,
                category, status, upvotes, likes_count, comments_count, is_deleted, created_at, updated_at
            )
            VALUES (
                :firebase_uid, :author_name, :author_avatar, :title, :content,
                :category, 'open', 0, 0, 0, false, NOW(), NOW()
            )
            RETURNING id, firebase_uid, author_name, author_avatar, title, content,
                      category, status, upvotes, likes_count, comments_count, is_pinned, is_deleted, created_at, updated_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "firebase_uid": firebase_uid,
                "author_name": author_name,
                "author_avatar": author_avatar,
                "title": title,
                "content": content,
                "category": category or "Discussion",
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to create community post")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def list_posts(
        self,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        """List community posts with pagination and optional category filter."""
        offset = (page - 1) * page_size

        where_clauses = []
        params: dict[str, Any] = {"limit": page_size, "offset": offset}

        if not include_deleted:
            where_clauses.append("is_deleted = false")

        if category and category.lower() != "all":
            where_clauses.append("LOWER(category) = LOWER(:category)")
            params["category"] = category

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        count_stmt = text(f"SELECT COUNT(*)::int FROM community_posts {where_sql}")
        total = self._db.execute(count_stmt, params).scalar() or 0

        query_stmt = text(
            f"""
            SELECT id, firebase_uid, author_name, author_avatar, title, content,
                   category, status, upvotes, likes_count, comments_count, is_pinned, is_deleted, created_at, updated_at
            FROM community_posts
            {where_sql}
            ORDER BY is_pinned DESC, created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        result = self._db.execute(query_stmt, params)
        posts = []
        for r in result.fetchall():
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            posts.append(d)

        return posts, total

    def count_comments_for_posts(self, post_ids: list[str]) -> dict[str, int]:
        """Return comment count map {post_id: count} for a list of post IDs."""
        if not post_ids:
            return {}

        stmt = text(
            """
            SELECT post_id::text, COUNT(*)::int AS count
            FROM community_comments
            WHERE post_id::text IN :post_ids AND is_deleted = false
            GROUP BY post_id
            """
        ).bindparams(bindparam("post_ids", expanding=True))

        try:
            result = self._db.execute(stmt, {"post_ids": list(post_ids)})
            counts: dict[str, int] = {}
            for r in result.fetchall():
                counts[r[0]] = r[1]
            return counts
        except Exception as e:
            logger.debug("count_comments_for_posts exception: %s", e)
            return {}


    def get_post_by_id(self, post_id: str, allow_deleted: bool = False) -> dict[str, Any] | None:
        """Fetch a single post by UUID."""
        stmt = text(
            """
            SELECT id, firebase_uid, author_name, author_avatar, title, content,
                   category, status, upvotes, likes_count, comments_count, is_pinned, is_deleted, created_at, updated_at
            FROM community_posts
            WHERE id::text = :post_id
            """
        )
        result = self._db.execute(stmt, {"post_id": post_id})
        row = result.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        if not allow_deleted and d.get("is_deleted"):
            return None
        d["id"] = str(d["id"])
        return d

    def update_post(
        self,
        post_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        is_deleted: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Update fields of a post."""
        sets = ["updated_at = NOW()"]
        params: dict[str, Any] = {"post_id": post_id}

        if title is not None:
            sets.append("title = :title")
            params["title"] = title
        if content is not None:
            sets.append("content = :content")
            params["content"] = content
        if category is not None:
            sets.append("category = :category")
            params["category"] = category
        if status is not None:
            sets.append("status = :status")
            params["status"] = status
        if is_pinned is not None:
            sets.append("is_pinned = :is_pinned")
            params["is_pinned"] = is_pinned
        if is_deleted is not None:
            sets.append("is_deleted = :is_deleted")
            params["is_deleted"] = is_deleted

        stmt = text(
            f"""
            UPDATE community_posts
            SET {", ".join(sets)}
            WHERE id::text = :post_id
            RETURNING id, firebase_uid, author_name, author_avatar, title, content,
                      category, status, upvotes, likes_count, comments_count, is_pinned, is_deleted, created_at, updated_at
            """
        )
        result = self._db.execute(stmt, params)
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise ValueError(f"Post {post_id} not found")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def delete_post(self, post_id: str, hard_delete: bool = False) -> bool:
        """Delete or soft-delete a post."""
        if hard_delete:
            stmt = text("DELETE FROM community_posts WHERE id::text = :post_id")
        else:
            stmt = text("UPDATE community_posts SET is_deleted = true, updated_at = NOW() WHERE id::text = :post_id")
        result = self._db.execute(stmt, {"post_id": post_id})
        self._db.commit()
        return result.rowcount > 0

    # ── Comments ──────────────────────────────────────────────────────────────

    def get_comments_for_post(self, post_id: str, allow_deleted: bool = False) -> list[dict[str, Any]]:
        """Fetch all comments for a post (with parent_id for threading)."""
        del_clause = "" if allow_deleted else "AND is_deleted = false"
        stmt = text(
            f"""
            SELECT id, post_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at
            FROM community_comments
            WHERE post_id::text = :post_id {del_clause}
            ORDER BY created_at ASC
            """
        )
        result = self._db.execute(stmt, {"post_id": post_id})
        comments = []
        for r in result.fetchall():
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            d["post_id"] = str(d["post_id"])
            if d.get("parent_id"):
                d["parent_id"] = str(d["parent_id"])
            comments.append(d)
        return comments

    def create_comment(
        self,
        post_id: str,
        firebase_uid: str,
        author_name: str,
        content: str,
        parent_id: Optional[str] = None,
        author_avatar: Optional[str] = None,
    ) -> dict[str, Any]:
        """Insert a new comment or reply on a community post."""
        stmt = text(
            """
            INSERT INTO community_comments (post_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at)
            VALUES (:post_id, :firebase_uid, :author_name, :author_avatar, :parent_id, :content, false, NOW(), NOW())
            RETURNING id, post_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "post_id": post_id,
                "firebase_uid": firebase_uid,
                "author_name": author_name,
                "author_avatar": author_avatar,
                "parent_id": parent_id,
                "content": content,
            },
        )
        # Increment comment count on post
        self._db.execute(
            text("UPDATE community_posts SET comments_count = comments_count + 1 WHERE id::text = :post_id"),
            {"post_id": post_id},
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to create community comment")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d["post_id"] = str(d["post_id"])
        if d.get("parent_id"):
            d["parent_id"] = str(d["parent_id"])
        return d

    def delete_comment(self, comment_id: str, hard_delete: bool = False) -> bool:
        """Delete or soft-delete a comment."""
        if hard_delete:
            stmt = text("DELETE FROM community_comments WHERE id::text = :comment_id")
        else:
            stmt = text("UPDATE community_comments SET is_deleted = true, updated_at = NOW() WHERE id::text = :comment_id")
        result = self._db.execute(stmt, {"comment_id": comment_id})
        self._db.commit()
        return result.rowcount > 0

    # ── Votes / Likes ─────────────────────────────────────────────────────────

    def toggle_upvote(self, post_id: str, firebase_uid: str) -> dict[str, Any]:
        """Toggle upvote/like for a user on a post in an atomic transaction."""
        chk_stmt = text(
            """
            SELECT id FROM community_post_votes
            WHERE post_id::text = :post_id AND firebase_uid = :firebase_uid
            """
        )
        chk_res = self._db.execute(chk_stmt, {"post_id": post_id, "firebase_uid": firebase_uid}).fetchone()

        post = self.get_post_by_id(post_id)
        if not post:
            raise ValueError(f"Post {post_id} not found")

        current_upvotes = post.get("upvotes", 0)

        if chk_res:
            del_stmt = text(
                """
                DELETE FROM community_post_votes
                WHERE post_id::text = :post_id AND firebase_uid = :firebase_uid
                """
            )
            self._db.execute(del_stmt, {"post_id": post_id, "firebase_uid": firebase_uid})
            new_upvotes = max(0, current_upvotes - 1)
            voted = False
        else:
            ins_stmt = text(
                """
                INSERT INTO community_post_votes (post_id, firebase_uid)
                VALUES (:post_id, :firebase_uid)
                """
            )
            self._db.execute(ins_stmt, {"post_id": post_id, "firebase_uid": firebase_uid})
            new_upvotes = current_upvotes + 1
            voted = True

        upd_stmt = text(
            """
            UPDATE community_posts
            SET upvotes = :upvotes, likes_count = :upvotes
            WHERE id::text = :post_id
            """
        )
        self._db.execute(upd_stmt, {"upvotes": new_upvotes, "post_id": post_id})
        self._db.commit()

        return {"upvotes": new_upvotes, "likes_count": new_upvotes, "voted": voted, "has_liked": voted}

    # ── Reports ───────────────────────────────────────────────────────────────

    def create_report(
        self,
        reporter_uid: str,
        target_type: str,
        target_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """File a report against inappropriate content."""
        stmt = text(
            """
            INSERT INTO content_reports (reporter_uid, target_type, target_id, reason, status, created_at)
            VALUES (:reporter_uid, :target_type, :target_id, :reason, 'pending', NOW())
            RETURNING id, reporter_uid, target_type, target_id, reason, status, created_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "reporter_uid": reporter_uid,
                "target_type": target_type,
                "target_id": target_id,
                "reason": reason,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to create report")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def list_reports(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        """List reports for admin review."""
        where = "WHERE status = :status" if status else ""
        stmt = text(
            f"""
            SELECT id, reporter_uid, target_type, target_id, reason, status, created_at
            FROM content_reports
            {where}
            ORDER BY created_at DESC
            """
        )
        result = self._db.execute(stmt, {"status": status} if status else {})
        return [dict(r._mapping) for r in result.fetchall()]

    def update_report_status(self, report_id: str, status: str) -> bool:
        """Update report status ('reviewed', 'dismissed', 'actioned')."""
        stmt = text("UPDATE content_reports SET status = :status WHERE id::text = :report_id")
        result = self._db.execute(stmt, {"status": status, "report_id": report_id})
        self._db.commit()
        return result.rowcount > 0

    # ── Paper Requests ────────────────────────────────────────────────────────

    def create_paper_request(
        self,
        firebase_uid: str,
        author_name: str,
        title: str,
        exam_type: str,
        year: int,
        month: Optional[str] = None,
        district: Optional[str] = None,
        description: Optional[str] = None,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        author_avatar: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new community paper request."""
        stmt = text(
            """
            INSERT INTO paper_requests (
                firebase_uid, author_name, author_avatar, title, exam_type, year,
                month, district, description, class_id, subject_id, status, created_at, updated_at
            )
            VALUES (
                :firebase_uid, :author_name, :author_avatar, :title, :exam_type, :year,
                :month, :district, :description, :class_id, :subject_id, 'open', NOW(), NOW()
            )
            RETURNING id, firebase_uid, author_name, author_avatar, title, exam_type, year,
                      month, district, description, class_id, subject_id, status, fulfilled_paper_id, created_at, updated_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "firebase_uid": firebase_uid,
                "author_name": author_name,
                "author_avatar": author_avatar,
                "title": title,
                "exam_type": exam_type,
                "year": year,
                "month": month,
                "district": district,
                "description": description,
                "class_id": class_id,
                "subject_id": subject_id,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to create paper request")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def list_paper_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """List paper requests with optional status filter."""
        offset = (page - 1) * page_size
        where = "WHERE pr.status = :status" if status else ""
        params: dict[str, Any] = {"limit": page_size, "offset": offset}
        if status:
            params["status"] = status

        count_stmt = text(f"SELECT COUNT(*)::int FROM paper_requests pr {where}")
        total = self._db.execute(count_stmt, params).scalar() or 0

        query_stmt = text(
            f"""
            SELECT pr.id, pr.firebase_uid, pr.author_name, pr.author_avatar, pr.title,
                   pr.exam_type, pr.year, pr.month, pr.district, pr.description,
                   pr.class_id, c.name AS class_name,
                   pr.subject_id, s.name AS subject_name,
                   pr.status, pr.fulfilled_paper_id, pr.created_at, pr.updated_at
            FROM paper_requests pr
            LEFT JOIN classes c ON pr.class_id = c.id
            LEFT JOIN subjects s ON pr.subject_id = s.id
            {where}
            ORDER BY pr.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        result = self._db.execute(query_stmt, params)
        requests = []
        for r in result.fetchall():
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            requests.append(d)

        return requests, total

    def update_paper_request(
        self,
        request_id: str,
        status: Optional[str] = None,
        fulfilled_paper_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Update status of a paper request."""
        sets = ["updated_at = NOW()"]
        params: dict[str, Any] = {"request_id": request_id}
        if status is not None:
            sets.append("status = :status")
            params["status"] = status
        if fulfilled_paper_id is not None:
            sets.append("fulfilled_paper_id = :fulfilled_paper_id")
            params["fulfilled_paper_id"] = fulfilled_paper_id

        stmt = text(
            f"""
            UPDATE paper_requests
            SET {", ".join(sets)}
            WHERE id::text = :request_id
            RETURNING id, firebase_uid, author_name, author_avatar, title, exam_type, year,
                      month, district, description, class_id, subject_id, status, fulfilled_paper_id, created_at, updated_at
            """
        )
        result = self._db.execute(stmt, params)
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise ValueError(f"Paper request {request_id} not found")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    # ── User Profile ──────────────────────────────────────────────────────────

    def get_user_profile(self, uid: str) -> dict[str, Any]:
        """
        Aggregate public profile for a community member/contributor.
        Strictly strips email to preserve privacy.
        """
        # Approved contributions
        appr_stmt = text(
            """
            SELECT COUNT(*)::int
            FROM submissions s
            JOIN submission_files f ON s.id = f.submission_id
            WHERE s.firebase_uid = :uid AND s.status = 'approved'
            """
        )
        approved_count = self._db.execute(appr_stmt, {"uid": uid}).scalar() or 0

        # Joined date (earliest submission or post)
        join_stmt = text(
            """
            SELECT MIN(created_at) AS joined
            FROM (
                SELECT created_at FROM submissions WHERE firebase_uid = :uid
                UNION ALL
                SELECT created_at FROM community_posts WHERE firebase_uid = :uid
            ) t
            """
        )
        joined_date = self._db.execute(join_stmt, {"uid": uid}).scalar() or datetime.now(timezone.utc)

        # Posts count
        post_stmt = text("SELECT COUNT(*)::int FROM community_posts WHERE firebase_uid = :uid AND is_deleted = false")
        posts_count = self._db.execute(post_stmt, {"uid": uid}).scalar() or 0

        # Comments count
        comm_stmt = text("SELECT COUNT(*)::int FROM community_comments WHERE firebase_uid = :uid AND is_deleted = false")
        comments_count = self._db.execute(comm_stmt, {"uid": uid}).scalar() or 0

        # Likes received
        likes_stmt = text(
            """
            SELECT COALESCE(SUM(upvotes), 0)::int
            FROM community_posts
            WHERE firebase_uid = :uid AND is_deleted = false
            """
        )
        likes_received = self._db.execute(likes_stmt, {"uid": uid}).scalar() or 0

        # Latest author name / avatar
        name_stmt = text(
            """
            SELECT author_name, author_avatar
            FROM community_posts
            WHERE firebase_uid = :uid
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        name_row = self._db.execute(name_stmt, {"uid": uid}).fetchone()
        display_name = (name_row.author_name if name_row else "Community Member")
        avatar_url = (name_row.author_avatar if name_row else None)

        from app.services.leaderboard_service import compute_badges
        badges = compute_badges(approved_count, 100.0 if approved_count > 0 else 0.0)

        return {
            "display_name": display_name,
            "avatar_url": avatar_url,
            "joined_date": joined_date,
            "approved_contributions": approved_count,
            "likes_received": likes_received,
            "posts_count": posts_count,
            "comments_count": comments_count,
            "badges": badges,
        }
