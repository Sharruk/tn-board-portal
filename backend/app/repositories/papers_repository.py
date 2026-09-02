"""
Papers repository — direct PostgreSQL data access for the `papers` table.

Uses SQLAlchemy Session with parameterized SQL.
"""

import json
import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.storage import get_storage_client

logger = logging.getLogger(__name__)


def _add_status(row: dict[str, Any]) -> dict[str, Any]:
    """
    Inject a synthesised status and description field so Pydantic schemas are satisfied.
    Visible papers have is_visible = true (published), hidden have is_visible = false (archived).
    """
    is_visible = row.get("is_visible", True)
    row.setdefault("status", "published" if is_visible else "archived")
    row.setdefault("description", None)
    return row


class PapersRepository:
    """Data access layer for the `papers` table."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._db = db
        self._storage = storage if storage is not None else get_storage_client()

    def get_by_id(self, paper_id: int, published_only: bool = True) -> dict[str, Any] | None:
        """
        Return one paper with full subject + class join, or None.
        """
        logger.debug("PapersRepository.get_by_id(paper_id=%s, published_only=%s)", paper_id, published_only)
        sql = """
            SELECT 
                p.id, p.subject_id, p.exam_type, p.year, p.month, p.district, p.title, p.description, p.paper_type,
                p.file_path, p.public_url, p.youtube_url, p.original_filename, p.is_visible,
                p.download_count, p.created_at,
                p.submission_id, p.contributor_name,
                s.name AS subject_name, s.slug AS subject_slug, s.is_practical,
                c.id AS class_id, c.name AS class_name, c.slug AS class_slug
            FROM papers p
            JOIN subjects s ON p.subject_id = s.id
            JOIN classes c ON s.class_id = c.id
            WHERE p.id = :paper_id
        """
        if published_only:
            sql += " AND p.is_visible = true"

        stmt = text(sql)
        result = self._db.execute(stmt, {"paper_id": paper_id})
        row = result.fetchone()

        if not row:
            return None
        d = dict(row._mapping)
        if d.get("submission_id"):
            d["submission_id"] = str(d["submission_id"])
        return _add_status(d)

    def delete_paper(
        self,
        paper_id: int,
        admin_id: str | None = None,
        admin_email: str | None = None,
        auto_commit: bool = True,
    ) -> tuple[bool, bool]:
        """
        Delete a paper record and its associated storage file in the 'papers' bucket.

        Returns:
            Tuple of (db_deleted: bool, storage_deleted: bool).
        """
        logger.debug(
            "PapersRepository.delete_paper(paper_id=%s, admin_email=%s, auto_commit=%s)",
            paper_id,
            admin_email,
            auto_commit,
        )

        # 1. Fetch the paper row (including hidden/archived)
        paper = self.get_by_id(paper_id, published_only=False)
        if not paper:
            return False, False

        file_path = paper.get("file_path")
        # If file_path is missing but public_url exists, attempt fallback extraction
        if not file_path and paper.get("public_url"):
            pub_url = paper["public_url"]
            if "/papers/" in pub_url:
                file_path = pub_url.split("/papers/")[-1].split("?")[0]

        # 2. Delete the storage object from the 'papers' bucket
        storage_deleted = False
        if file_path:
            try:
                self._storage.from_("papers").remove([file_path])
                storage_deleted = True
                logger.info("Deleted storage object '%s' for paper %s", file_path, paper_id)
            except Exception as exc:
                err_str = str(exc).lower()
                if "not found" in err_str or "404" in err_str or "resource not found" in err_str:
                    logger.warning(
                        "Storage object '%s' already missing for paper %s: %s",
                        file_path,
                        paper_id,
                        exc,
                    )
                    storage_deleted = False
                else:
                    logger.error(
                        "Failed to delete storage object '%s' for paper %s: %s",
                        file_path,
                        paper_id,
                        exc,
                    )
                    raise RuntimeError(
                        f"Failed to delete paper file from storage: {exc}"
                    ) from exc

        try:
            # 3. Delete database record
            del_stmt = text("DELETE FROM papers WHERE id = :paper_id")
            self._db.execute(del_stmt, {"paper_id": paper_id})

            # 4. Insert audit log
            # Note: audit_logs.admin_id REFERENCES auth.users(id) (Supabase Auth).
            # When Firebase Auth is used, admin_id is a Firebase UID, so we store it
            # inside target_details JSONB and pass NULL for the UUID column to prevent type/FK errors.
            # target_paper_id is set to NULL since the paper row is deleted.
            try:
                audit_stmt = text(
                    """
                    INSERT INTO audit_logs (admin_id, admin_email, action, target_paper_id, target_details, created_at)
                    VALUES (NULL, :admin_email, 'delete', NULL, :details, NOW())
                    """
                )
                details = json.dumps(
                    {
                        "paper_id": paper_id,
                        "admin_uid": admin_id,
                        "admin_email": admin_email,
                        "title": paper.get("title"),
                        "exam_type": paper.get("exam_type"),
                        "year": paper.get("year"),
                        "class_name": paper.get("class_name"),
                        "subject_name": paper.get("subject_name"),
                        "file_path": file_path,
                        "original_filename": paper.get("original_filename"),
                        "contributor_name": paper.get("contributor_name"),
                    }
                )
                self._db.execute(
                    audit_stmt,
                    {
                        "admin_email": admin_email,
                        "details": details,
                    },
                )
            except Exception as a_err:
                logger.warning("Failed to insert audit log for deleted paper %s: %s", paper_id, a_err)

            if auto_commit:
                self._db.commit()

            return True, storage_deleted
        except Exception as db_err:
            if auto_commit:
                self._db.rollback()
            logger.error("Failed to delete paper record %s from database: %s", paper_id, db_err)
            raise

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the N most recently uploaded visible papers.
        """
        logger.debug("PapersRepository.list_recent(limit=%s)", limit)
        stmt = text(
            """
            SELECT 
                id, subject_id, exam_type, year, month, district, title, paper_type,
                public_url, youtube_url, original_filename, is_visible,
                download_count, contributor_name, submission_id, created_at
            FROM papers
            WHERE is_visible = true
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )
        result = self._db.execute(stmt, {"limit": limit})
        return [_add_status(dict(row._mapping)) for row in result.fetchall()]

    def list_popular(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Return the N most downloaded visible papers.
        """
        logger.debug("PapersRepository.list_popular(limit=%s)", limit)
        stmt = text(
            """
            SELECT 
                id, subject_id, exam_type, year, month, district, title, paper_type,
                public_url, youtube_url, original_filename, is_visible,
                download_count, contributor_name, submission_id, created_at
            FROM papers
            WHERE is_visible = true
            ORDER BY download_count DESC
            LIMIT :limit
            """
        )
        result = self._db.execute(stmt, {"limit": limit})
        return [_add_status(dict(row._mapping)) for row in result.fetchall()]

    def list_by_subject(
        self,
        subject_id: int,
        exam_type: str | None = None,
        paper_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return all visible papers for a given subject.
        """
        logger.debug(
            "PapersRepository.list_by_subject(subject_id=%s, exam_type=%s, paper_type=%s)",
            subject_id, exam_type, paper_type,
        )
        conditions = ["subject_id = :subject_id", "is_visible = true"]
        params: dict[str, Any] = {"subject_id": subject_id}

        if exam_type:
            conditions.append("exam_type = :exam_type")
            params["exam_type"] = exam_type
        if paper_type:
            conditions.append("paper_type = :paper_type")
            params["paper_type"] = paper_type

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT 
                id, subject_id, exam_type, year, month, district, title, paper_type,
                public_url, youtube_url, original_filename, is_visible,
                download_count, contributor_name, submission_id, created_at
            FROM papers
            WHERE {where_clause}
            ORDER BY year DESC
        """
        stmt = text(sql)
        result = self._db.execute(stmt, params)
        return [_add_status(dict(row._mapping)) for row in result.fetchall()]

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
        Search visible papers using direct SQL joining papers, subjects, and classes.
        """
        logger.debug(
            "PapersRepository.search(q=%r, class_id=%s, exam_type=%s, paper_type=%s, month=%s, district=%s)",
            q, class_id, exam_type, paper_type, month, district,
        )
        conditions = ["p.is_visible = true"]
        params: dict[str, Any] = {"like": f"%{q}%"}

        # Search matching condition across paper fields + subject + class
        conditions.append(
            """(
                p.title ILIKE :like OR
                p.exam_type ILIKE :like OR
                COALESCE(p.month, '') ILIKE :like OR
                COALESCE(p.district, '') ILIKE :like OR
                s.name ILIKE :like OR
                c.name ILIKE :like
            )"""
        )

        if class_id is not None:
            conditions.append("c.id = :class_id")
            params["class_id"] = class_id
        if exam_type:
            conditions.append("p.exam_type = :exam_type")
            params["exam_type"] = exam_type
        if paper_type:
            conditions.append("p.paper_type = :paper_type")
            params["paper_type"] = paper_type
        if month:
            conditions.append("p.month = :month")
            params["month"] = month
        if district:
            conditions.append("p.district ILIKE :district_filter")
            params["district_filter"] = f"%{district}%"

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT 
                p.id, p.subject_id, p.exam_type, p.year, p.month, p.district, p.title, p.paper_type,
                p.public_url, p.youtube_url, p.original_filename, p.is_visible, p.download_count, p.contributor_name, p.submission_id, p.created_at,
                s.name AS subject_name,
                c.id AS class_id, c.name AS class_name
            FROM papers p
            JOIN subjects s ON p.subject_id = s.id
            JOIN classes c ON s.class_id = c.id
            WHERE {where_clause}
            ORDER BY p.created_at DESC
            LIMIT 50
        """
        stmt = text(sql)
        result = self._db.execute(stmt, params)
        return [_add_status(dict(row._mapping)) for row in result.fetchall()]


    def record_download(
        self,
        paper_id: int,
        user_id: str | None = None,
        user_email: str | None = None,
    ) -> None:
        """
        Atomically increment download_count for a visible paper and record log event.
        """
        logger.debug("PapersRepository.record_download(paper_id=%s)", paper_id)
        stmt = text(
            """
            UPDATE papers
            SET download_count = download_count + 1
            WHERE id = :paper_id AND is_visible = true
            RETURNING id, download_count
            """
        )
        result = self._db.execute(stmt, {"paper_id": paper_id})
        row = result.fetchone()
        if not row:
            self._db.rollback()
            raise ValueError(f"Paper {paper_id} not found or not visible")

        if user_id or user_email:
            try:
                log_stmt = text(
                    """
                    INSERT INTO download_logs (firebase_uid, email, paper_id)
                    VALUES (:uid, :email, :paper_id)
                    """
                )
                self._db.execute(
                    log_stmt,
                    {"uid": user_id, "email": user_email, "paper_id": paper_id},
                )
            except Exception as e:
                logger.warning("Failed to insert download_log: %s", e)

        self._db.commit()

    # ── Paper Likes ───────────────────────────────────────────────────────────

    def toggle_like(self, paper_id: int, firebase_uid: str) -> dict[str, Any]:
        """Toggle like for user on paper in an atomic transaction."""
        chk_stmt = text(
            "SELECT id FROM paper_likes WHERE paper_id = :paper_id AND firebase_uid = :firebase_uid"
        )
        existing = self._db.execute(chk_stmt, {"paper_id": paper_id, "firebase_uid": firebase_uid}).fetchone()

        if existing:
            self._db.execute(
                text("DELETE FROM paper_likes WHERE paper_id = :paper_id AND firebase_uid = :firebase_uid"),
                {"paper_id": paper_id, "firebase_uid": firebase_uid},
            )
            has_liked = False
        else:
            self._db.execute(
                text("INSERT INTO paper_likes (paper_id, firebase_uid, created_at) VALUES (:paper_id, :firebase_uid, NOW())"),
                {"paper_id": paper_id, "firebase_uid": firebase_uid},
            )
            has_liked = True

        cnt_stmt = text("SELECT COUNT(*)::int FROM paper_likes WHERE paper_id = :paper_id")
        likes_count = self._db.execute(cnt_stmt, {"paper_id": paper_id}).scalar() or 0
        self._db.commit()

        return {"paper_id": paper_id, "likes_count": likes_count, "has_liked": has_liked}

    def get_likes_info(self, paper_id: int, firebase_uid: Optional[str] = None) -> dict[str, Any]:
        """Get total like count and whether current user has liked."""
        cnt_stmt = text("SELECT COUNT(*)::int FROM paper_likes WHERE paper_id = :paper_id")
        likes_count = self._db.execute(cnt_stmt, {"paper_id": paper_id}).scalar() or 0

        has_liked = False
        if firebase_uid:
            chk_stmt = text(
                "SELECT id FROM paper_likes WHERE paper_id = :paper_id AND firebase_uid = :firebase_uid"
            )
            has_liked = bool(self._db.execute(chk_stmt, {"paper_id": paper_id, "firebase_uid": firebase_uid}).fetchone())

        return {"paper_id": paper_id, "likes_count": likes_count, "has_liked": has_liked}

    # ── Paper Comments ────────────────────────────────────────────────────────

    def get_comments_for_paper(self, paper_id: int) -> list[dict[str, Any]]:
        """Fetch all non-deleted comments for a paper."""
        stmt = text(
            """
            SELECT id, paper_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at
            FROM paper_comments
            WHERE paper_id = :paper_id AND is_deleted = false
            ORDER BY created_at ASC
            """
        )
        result = self._db.execute(stmt, {"paper_id": paper_id})
        comments = []
        for r in result.fetchall():
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            if d.get("parent_id"):
                d["parent_id"] = str(d["parent_id"])
            comments.append(d)
        return comments

    def add_paper_comment(
        self,
        paper_id: int,
        firebase_uid: str,
        author_name: str,
        content: str,
        parent_id: Optional[str] = None,
        author_avatar: Optional[str] = None,
    ) -> dict[str, Any]:
        """Insert a comment or reply on a paper."""
        stmt = text(
            """
            INSERT INTO paper_comments (paper_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at)
            VALUES (:paper_id, :firebase_uid, :author_name, :author_avatar, :parent_id, :content, false, NOW(), NOW())
            RETURNING id, paper_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "paper_id": paper_id,
                "firebase_uid": firebase_uid,
                "author_name": author_name,
                "author_avatar": author_avatar,
                "parent_id": parent_id,
                "content": content,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to add paper comment")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        if d.get("parent_id"):
            d["parent_id"] = str(d["parent_id"])
        return d

    def delete_paper_comment(self, comment_id: str, hard_delete: bool = False) -> bool:
        """Delete or soft-delete a paper comment."""
        if hard_delete:
            stmt = text("DELETE FROM paper_comments WHERE id::text = :comment_id")
        else:
            stmt = text("UPDATE paper_comments SET is_deleted = true, updated_at = NOW() WHERE id::text = :comment_id")
        result = self._db.execute(stmt, {"comment_id": comment_id})
        self._db.commit()
        return result.rowcount > 0


