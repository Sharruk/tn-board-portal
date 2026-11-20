"""
Study Materials repository — PostgreSQL data access for study_materials and material_files tables.
"""

import logging
import re
import uuid
from typing import Any, List, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _slugify(text_val: str) -> str:
    """Generate a clean URL-safe slug from a title."""
    s = text_val.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s[:280] or "material"


class StudyMaterialsRepository:
    """Data access layer for study_materials and material_files."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Single Item Retrieval ──────────────────────────────────────────────────

    def get_by_id(self, material_id: UUID | str, published_only: bool = True) -> Optional[dict[str, Any]]:
        """Retrieve single material with joined class, subject, category and files."""
        conditions = ["sm.id = :id"]
        params: dict[str, Any] = {"id": str(material_id)}

        if published_only:
            conditions.append("sm.status = 'published'")

        where_clause = " AND ".join(conditions)
        stmt = text(
            f"""
            SELECT 
                sm.id, sm.title, sm.slug, sm.description, sm.class_id, sm.subject_id, sm.category_id,
                sm.medium, sm.question_formats, sm.tags, sm.academic_year, sm.author_name, sm.author_organization,
                sm.status, sm.view_count, sm.download_count, sm.created_by, sm.updated_by,
                sm.created_at, sm.updated_at,
                c.name AS class_name,
                s.name AS subject_name,
                mc.name AS category_name,
                mc.slug AS category_slug
            FROM study_materials sm
            LEFT JOIN classes c ON sm.class_id = c.id
            LEFT JOIN subjects s ON sm.subject_id = s.id
            LEFT JOIN material_categories mc ON sm.category_id = mc.id
            WHERE {where_clause}
            """
        )
        row = self._db.execute(stmt, params).fetchone()
        if not row:
            return None

        data = dict(row._mapping)
        data["files"] = self.get_files(data["id"])
        return data

    def get_by_slug(self, slug: str, published_only: bool = True) -> Optional[dict[str, Any]]:
        """Retrieve single material by slug with joined metadata and files."""
        conditions = ["sm.slug = :slug"]
        params: dict[str, Any] = {"slug": slug}

        if published_only:
            conditions.append("sm.status = 'published'")

        where_clause = " AND ".join(conditions)
        stmt = text(
            f"""
            SELECT 
                sm.id, sm.title, sm.slug, sm.description, sm.class_id, sm.subject_id, sm.category_id,
                sm.medium, sm.question_formats, sm.tags, sm.academic_year, sm.author_name, sm.author_organization,
                sm.status, sm.view_count, sm.download_count, sm.created_by, sm.updated_by,
                sm.created_at, sm.updated_at,
                c.name AS class_name,
                s.name AS subject_name,
                mc.name AS category_name,
                mc.slug AS category_slug
            FROM study_materials sm
            LEFT JOIN classes c ON sm.class_id = c.id
            LEFT JOIN subjects s ON sm.subject_id = s.id
            LEFT JOIN material_categories mc ON sm.category_id = mc.id
            WHERE {where_clause}
            """
        )
        row = self._db.execute(stmt, params).fetchone()
        if not row:
            return None

        data = dict(row._mapping)
        data["files"] = self.get_files(data["id"])
        return data

    # ── List / Filtered Query ──────────────────────────────────────────────────

    def list_materials(
        self,
        *,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        class_general_only: bool = False,
        category_id: Optional[int] = None,
        medium: Optional[str] = None,
        tag: Optional[str] = None,
        question_format: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        published_only: bool = True,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Query materials with dynamic filters and pagination.
        Returns (list_of_materials, total_count).
        """
        conditions: list[str] = []
        params: dict[str, Any] = {}

        if published_only:
            conditions.append("sm.status = 'published'")
        elif status:
            conditions.append("sm.status = :status")
            params["status"] = status

        if class_id is not None:
            conditions.append("sm.class_id = :class_id")
            params["class_id"] = class_id

        if class_general_only:
            conditions.append("sm.subject_id IS NULL")
        elif subject_id is not None:
            conditions.append("sm.subject_id = :subject_id")
            params["subject_id"] = subject_id

        if category_id is not None:
            conditions.append("sm.category_id = :category_id")
            params["category_id"] = category_id

        if medium:
            conditions.append("(sm.medium = :medium OR sm.medium = 'both')")
            params["medium"] = medium

        if tag:
            clean_tag = tag.strip().lower()
            conditions.append("sm.tags @> ARRAY[:tag]::text[]")
            params["tag"] = clean_tag

        if question_format:
            conditions.append("sm.question_formats @> ARRAY[:q_format]::varchar[]")
            params["q_format"] = question_format

        if search:
            conditions.append("(sm.title ILIKE :search OR sm.description ILIKE :search OR sm.author_name ILIKE :search)")
            params["search"] = f"%{search.strip()}%"

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count total
        count_stmt = text(f"SELECT COUNT(*)::int FROM study_materials sm {where_clause}")
        total = self._db.execute(count_stmt, params).scalar() or 0

        # Query page
        offset = max(0, (page - 1) * limit)
        params["limit"] = limit
        params["offset"] = offset

        query_stmt = text(
            f"""
            SELECT 
                sm.id, sm.title, sm.slug, sm.class_id, sm.subject_id, sm.category_id,
                sm.medium, sm.question_formats, sm.tags, sm.academic_year, sm.author_name,
                sm.status, sm.view_count, sm.download_count,
                sm.created_at, sm.updated_at,
                c.name AS class_name,
                s.name AS subject_name,
                mc.name AS category_name,
                mc.slug AS category_slug,
                (SELECT COUNT(*)::int FROM material_files mf WHERE mf.material_id = sm.id) AS file_count,
                COALESCE((SELECT SUM(mf.file_size)::bigint FROM material_files mf WHERE mf.material_id = sm.id), 0) AS total_size_bytes
            FROM study_materials sm
            LEFT JOIN classes c ON sm.class_id = c.id
            LEFT JOIN subjects s ON sm.subject_id = s.id
            LEFT JOIN material_categories mc ON sm.category_id = mc.id
            {where_clause}
            ORDER BY sm.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        rows = self._db.execute(query_stmt, params).fetchall()
        return [dict(r._mapping) for r in rows], total

    # ── Create & Update Operations ─────────────────────────────────────────────

    def create_material(
        self,
        *,
        title: str,
        class_id: int,
        subject_id: Optional[int] = None,
        category_id: Optional[int] = None,
        description: Optional[str] = None,
        medium: str = "both",
        question_formats: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        academic_year: Optional[str] = None,
        author_name: Optional[str] = None,
        author_organization: Optional[str] = None,
        status: str = "draft",
        created_by: Optional[UUID | str] = None,
        slug: Optional[str] = None,
    ) -> dict[str, Any]:
        """Insert a new study material record."""
        base_slug = slug or _slugify(title)
        final_slug = base_slug

        chk_stmt = text("SELECT id FROM study_materials WHERE slug = :slug")
        if self._db.execute(chk_stmt, {"slug": final_slug}).fetchone():
            final_slug = f"{base_slug[:270]}-{uuid.uuid4().hex[:6]}"

        stmt = text(
            """
            INSERT INTO study_materials (
                title, slug, description, class_id, subject_id, category_id,
                medium, question_formats, tags, academic_year, author_name, author_organization,
                status, view_count, download_count, created_by, updated_by, created_at, updated_at
            )
            VALUES (
                :title, :slug, :description, :class_id, :subject_id, :category_id,
                :medium, :question_formats, :tags, :academic_year, :author_name, :author_organization,
                :status, 0, 0, :created_by, :created_by, NOW(), NOW()
            )
            RETURNING id, title, slug, description, class_id, subject_id, category_id,
                      medium, question_formats, tags, academic_year, author_name, author_organization,
                      status, view_count, download_count, created_by, updated_by, created_at, updated_at
            """
        )
        row = self._db.execute(
            stmt,
            {
                "title": title,
                "slug": final_slug,
                "description": description,
                "class_id": class_id,
                "subject_id": subject_id,
                "category_id": category_id,
                "medium": medium,
                "question_formats": question_formats or [],
                "tags": tags or [],
                "academic_year": academic_year,
                "author_name": author_name,
                "author_organization": author_organization,
                "status": status,
                "created_by": str(created_by) if created_by else None,
            },
        ).fetchone()
        self._db.commit()
        return dict(row._mapping)

    def update_material(
        self,
        material_id: UUID | str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        clear_subject: bool = False,
        category_id: Optional[int] = None,
        clear_category: bool = False,
        medium: Optional[str] = None,
        question_formats: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        academic_year: Optional[str] = None,
        author_name: Optional[str] = None,
        author_organization: Optional[str] = None,
        status: Optional[str] = None,
        updated_by: Optional[UUID | str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update study material fields."""
        fields = ["updated_at = NOW()"]
        params: dict[str, Any] = {"id": str(material_id)}

        if title is not None:
            fields.append("title = :title")
            params["title"] = title
        if description is not None:
            fields.append("description = :description")
            params["description"] = description
        if class_id is not None:
            fields.append("class_id = :class_id")
            params["class_id"] = class_id
        if clear_subject:
            fields.append("subject_id = NULL")
        elif subject_id is not None:
            fields.append("subject_id = :subject_id")
            params["subject_id"] = subject_id
        if clear_category:
            fields.append("category_id = NULL")
        elif category_id is not None:
            fields.append("category_id = :category_id")
            params["category_id"] = category_id
        if medium is not None:
            fields.append("medium = :medium")
            params["medium"] = medium
        if question_formats is not None:
            fields.append("question_formats = :question_formats")
            params["question_formats"] = question_formats
        if tags is not None:
            fields.append("tags = :tags")
            params["tags"] = tags
        if academic_year is not None:
            fields.append("academic_year = :academic_year")
            params["academic_year"] = academic_year
        if author_name is not None:
            fields.append("author_name = :author_name")
            params["author_name"] = author_name
        if author_organization is not None:
            fields.append("author_organization = :author_organization")
            params["author_organization"] = author_organization
        if status is not None:
            fields.append("status = :status")
            params["status"] = status
        if updated_by is not None:
            fields.append("updated_by = :updated_by")
            params["updated_by"] = str(updated_by)

        stmt = text(
            f"""
            UPDATE study_materials
            SET {', '.join(fields)}
            WHERE id = :id
            RETURNING id, title, slug, description, class_id, subject_id, category_id,
                      medium, question_formats, tags, academic_year, author_name, author_organization,
                      status, view_count, download_count, created_by, updated_by, created_at, updated_at
            """
        )
        row = self._db.execute(stmt, params).fetchone()
        self._db.commit()
        return dict(row._mapping) if row else None

    def update_status(self, material_id: UUID | str, status: str, updated_by: Optional[UUID | str] = None) -> Optional[dict[str, Any]]:
        """Quick status change (draft, published, archived)."""
        stmt = text(
            """
            UPDATE study_materials
            SET status = :status, updated_by = :updated_by, updated_at = NOW()
            WHERE id = :id
            RETURNING id, status, updated_at
            """
        )
        row = self._db.execute(
            stmt,
            {"id": str(material_id), "status": status, "updated_by": str(updated_by) if updated_by else None},
        ).fetchone()
        self._db.commit()
        return dict(row._mapping) if row else None

    def delete_material(self, material_id: UUID | str) -> bool:
        """Permanently delete material (cascades to material_files)."""
        stmt = text("DELETE FROM study_materials WHERE id = :id RETURNING id")
        row = self._db.execute(stmt, {"id": str(material_id)}).fetchone()
        self._db.commit()
        return bool(row)

    def increment_view_count(self, material_id: UUID | str) -> None:
        """Atomically increment view count."""
        stmt = text("UPDATE study_materials SET view_count = view_count + 1 WHERE id = :id")
        self._db.execute(stmt, {"id": str(material_id)})
        self._db.commit()

    def increment_download_count(self, material_id: UUID | str, file_id: Optional[UUID | str] = None) -> None:
        """Atomically increment download counts on material and optional specific file."""
        self._db.execute(
            text("UPDATE study_materials SET download_count = download_count + 1 WHERE id = :id"),
            {"id": str(material_id)},
        )
        if file_id:
            self._db.execute(
                text("UPDATE material_files SET download_count = download_count + 1 WHERE id = :file_id"),
                {"file_id": str(file_id)},
            )
        self._db.commit()

    # ── File Attachment Operations ─────────────────────────────────────────────

    def add_file(
        self,
        *,
        material_id: UUID | str,
        file_title: str,
        display_filename: str,
        file_type: str = "pdf",
        mime_type: Optional[str] = None,
        file_size: int = 0,
        bucket_name: Optional[str] = None,
        storage_path: Optional[str] = None,
        external_url: Optional[str] = None,
        sort_order: int = 0,
    ) -> dict[str, Any]:
        """Add an attachment file or external link to a study material."""
        stmt = text(
            """
            INSERT INTO material_files (
                material_id, file_title, display_filename, file_type, mime_type,
                file_size, bucket_name, storage_path, external_url, sort_order, download_count, created_at
            )
            VALUES (
                :material_id, :file_title, :display_filename, :file_type, :mime_type,
                :file_size, :bucket_name, :storage_path, :external_url, :sort_order, 0, NOW()
            )
            RETURNING id, material_id, file_title, display_filename, file_type, mime_type,
                      file_size, bucket_name, storage_path, external_url, sort_order, download_count, created_at
            """
        )
        row = self._db.execute(
            stmt,
            {
                "material_id": str(material_id),
                "file_title": file_title,
                "display_filename": display_filename,
                "file_type": file_type,
                "mime_type": mime_type,
                "file_size": file_size,
                "bucket_name": bucket_name,
                "storage_path": storage_path,
                "external_url": external_url,
                "sort_order": sort_order,
            },
        ).fetchone()
        self._db.commit()
        return dict(row._mapping)

    def get_files(self, material_id: UUID | str) -> list[dict[str, Any]]:
        """Get all attachments for a material ordered by sort_order."""
        stmt = text(
            """
            SELECT 
                id, material_id, file_title, display_filename, file_type, mime_type,
                file_size, bucket_name, storage_path, external_url, sort_order, download_count, created_at
            FROM material_files
            WHERE material_id = :material_id
            ORDER BY sort_order ASC, created_at ASC
            """
        )
        rows = self._db.execute(stmt, {"material_id": str(material_id)}).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_file_by_id(self, file_id: UUID | str) -> Optional[dict[str, Any]]:
        """Get single attachment by file ID."""
        stmt = text(
            """
            SELECT 
                id, material_id, file_title, display_filename, file_type, mime_type,
                file_size, bucket_name, storage_path, external_url, sort_order, download_count, created_at
            FROM material_files
            WHERE id = :id
            """
        )
        row = self._db.execute(stmt, {"id": str(file_id)}).fetchone()
        return dict(row._mapping) if row else None

    def update_file_storage(
        self,
        file_id: UUID | str,
        *,
        bucket_name: str,
        storage_path: str,
    ) -> Optional[dict[str, Any]]:
        """Update storage reference when a file is promoted from private staging to public CDN."""
        stmt = text(
            """
            UPDATE material_files
            SET bucket_name = :bucket_name, storage_path = :storage_path
            WHERE id = :id
            RETURNING id, bucket_name, storage_path
            """
        )
        row = self._db.execute(
            stmt,
            {"id": str(file_id), "bucket_name": bucket_name, "storage_path": storage_path},
        ).fetchone()
        self._db.commit()
        return dict(row._mapping) if row else None

    def update_file_display_name(self, file_id: UUID | str, display_filename: str) -> Optional[dict[str, Any]]:
        """Update display filename of an attachment file."""
        stmt = text(
            """
            UPDATE material_files
            SET display_filename = :display_filename
            WHERE id = :id
            RETURNING id, display_filename
            """
        )
        row = self._db.execute(stmt, {"id": str(file_id), "display_filename": display_filename}).fetchone()
        self._db.commit()
        return dict(row._mapping) if row else None

    def delete_file(self, file_id: UUID | str) -> Optional[dict[str, Any]]:
        """Delete single file attachment from database."""
        stmt = text(
            """
            DELETE FROM material_files
            WHERE id = :id
            RETURNING id, material_id, bucket_name, storage_path
            """
        )
        row = self._db.execute(stmt, {"id": str(file_id)}).fetchone()
        self._db.commit()
        return dict(row._mapping) if row else None

    # ── Study Material Likes ──────────────────────────────────────────────────

    def toggle_like(self, material_id: UUID | str, firebase_uid: str) -> dict[str, Any]:
        """Toggle like for user on study material in an atomic transaction."""
        mat_id_str = str(material_id)
        try:
            chk_stmt = text(
                "SELECT id FROM study_material_likes WHERE material_id = :material_id AND firebase_uid = :firebase_uid"
            )
            existing = self._db.execute(chk_stmt, {"material_id": mat_id_str, "firebase_uid": firebase_uid}).fetchone()

            if existing:
                self._db.execute(
                    text("DELETE FROM study_material_likes WHERE material_id = :material_id AND firebase_uid = :firebase_uid"),
                    {"material_id": mat_id_str, "firebase_uid": firebase_uid},
                )
                has_liked = False
            else:
                self._db.execute(
                    text("INSERT INTO study_material_likes (material_id, firebase_uid, created_at) VALUES (:material_id, :firebase_uid, NOW())"),
                    {"material_id": mat_id_str, "firebase_uid": firebase_uid},
                )
                has_liked = True

            cnt_stmt = text("SELECT COUNT(*)::int FROM study_material_likes WHERE material_id = :material_id")
            likes_count = self._db.execute(cnt_stmt, {"material_id": mat_id_str}).scalar() or 0
            self._db.commit()

            return {"material_id": material_id, "likes_count": likes_count, "has_liked": has_liked}
        except Exception:
            self._db.rollback()
            raise

    def get_likes_info(self, material_id: UUID | str, firebase_uid: Optional[str] = None) -> dict[str, Any]:
        """Get total like count and whether current user has liked."""
        mat_id_str = str(material_id)
        cnt_stmt = text("SELECT COUNT(*)::int FROM study_material_likes WHERE material_id = :material_id")
        likes_count = self._db.execute(cnt_stmt, {"material_id": mat_id_str}).scalar() or 0

        has_liked = False
        if firebase_uid:
            chk_stmt = text(
                "SELECT id FROM study_material_likes WHERE material_id = :material_id AND firebase_uid = :firebase_uid"
            )
            has_liked = bool(self._db.execute(chk_stmt, {"material_id": mat_id_str, "firebase_uid": firebase_uid}).fetchone())

        return {"material_id": material_id, "likes_count": likes_count, "has_liked": has_liked}

    # ── Study Material Comments ───────────────────────────────────────────────

    def get_comments_for_material(self, material_id: UUID | str) -> list[dict[str, Any]]:
        """Fetch all non-deleted comments for a study material with resolved author info."""
        stmt = text(
            """
            SELECT smc.id, smc.material_id, smc.firebase_uid,
                   COALESCE(NULLIF(TRIM(u.display_name), ''), smc.author_name) AS author_name,
                   COALESCE(NULLIF(TRIM(u.photo_url), ''), smc.author_avatar) AS author_avatar,
                   smc.parent_id, smc.content, smc.is_deleted, smc.created_at, smc.updated_at
            FROM study_material_comments smc
            LEFT JOIN users u ON smc.firebase_uid = u.firebase_uid
            WHERE smc.material_id = :material_id AND smc.is_deleted = false
            ORDER BY smc.created_at ASC
            """
        )
        result = self._db.execute(stmt, {"material_id": str(material_id)})
        comments = []
        for r in result.fetchall():
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            if d.get("parent_id"):
                d["parent_id"] = str(d["parent_id"])
            comments.append(d)
        return comments

    def add_material_comment(
        self,
        material_id: UUID | str,
        firebase_uid: str,
        author_name: str,
        content: str,
        parent_id: Optional[str] = None,
        author_avatar: Optional[str] = None,
    ) -> dict[str, Any]:
        """Insert a comment or reply on a study material."""
        stmt = text(
            """
            INSERT INTO study_material_comments (material_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at)
            VALUES (:material_id, :firebase_uid, :author_name, :author_avatar, :parent_id, :content, false, NOW(), NOW())
            RETURNING id, material_id, firebase_uid, author_name, author_avatar, parent_id, content, is_deleted, created_at, updated_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "material_id": str(material_id),
                "firebase_uid": firebase_uid,
                "author_name": author_name,
                "author_avatar": author_avatar,
                "parent_id": str(parent_id) if parent_id else None,
                "content": content,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to add study material comment")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        if d.get("parent_id"):
            d["parent_id"] = str(d["parent_id"])
        return d

    def delete_material_comment(self, comment_id: str, hard_delete: bool = False, auto_commit: bool = True) -> bool:
        """Delete or soft-delete a study material comment."""
        if hard_delete:
            stmt = text("DELETE FROM study_material_comments WHERE id::text = :comment_id")
        else:
            stmt = text("UPDATE study_material_comments SET is_deleted = true, updated_at = NOW() WHERE id::text = :comment_id")
        result = self._db.execute(stmt, {"comment_id": str(comment_id)})
        if auto_commit:
            self._db.commit()
        return result.rowcount > 0

