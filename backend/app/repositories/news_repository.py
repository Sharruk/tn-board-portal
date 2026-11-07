"""
News & Updates repository — direct PostgreSQL access for the news_updates table.
"""

import logging
import re
from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _slugify(text_val: str) -> str:
    """Generate a clean URL-safe slug from a title."""
    s = text_val.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s[:400] or "news"


class NewsRepository:
    """Data access layer for news_updates."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_news(
        self,
        *,
        title: str,
        category: str,
        summary: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None,
        thumbnail_url: Optional[str] = None,
        thumbnail_alt: Optional[str] = None,
        youtube_url: Optional[str] = None,
        pdf_url: Optional[str] = None,
        class_id: Optional[int] = None,
        district: Optional[str] = None,
        status: str = "draft",
        is_pinned: bool = False,
        published_at: Optional[Any] = None,
        slug: Optional[str] = None,
        auto_commit: bool = True,
    ) -> dict[str, Any]:
        """Insert a new news article."""
        final_slug = slug or _slugify(title)
        # Ensure slug uniqueness
        chk_stmt = text("SELECT id FROM news_updates WHERE slug = :slug")
        if self._db.execute(chk_stmt, {"slug": final_slug}).fetchone():
            import uuid
            final_slug = f"{final_slug[:380]}-{uuid.uuid4().hex[:6]}"

        stmt = text(
            """
            INSERT INTO news_updates (
                title, slug, summary, content, category, tags,
                thumbnail_url, thumbnail_alt, youtube_url, pdf_url,
                class_id, district, status, is_pinned, view_count,
                published_at, created_at, updated_at
            )
            VALUES (
                :title, :slug, :summary, :content, :category, :tags,
                :thumbnail_url, :thumbnail_alt, :youtube_url, :pdf_url,
                :class_id, :district, :status, :is_pinned, 0,
                :published_at, NOW(), NOW()
            )
            RETURNING id, title, slug, summary, content, category, tags,
                      thumbnail_url, thumbnail_alt, youtube_url, pdf_url,
                      class_id, district, status, is_pinned, view_count,
                      published_at, created_at, updated_at
            """
        )
        res = self._db.execute(
            stmt,
            {
                "title": title.strip(),
                "slug": final_slug,
                "summary": summary.strip() if summary else None,
                "content": content.strip() if content else None,
                "category": category.strip(),
                "tags": tags or [],
                "thumbnail_url": thumbnail_url,
                "thumbnail_alt": thumbnail_alt,
                "youtube_url": youtube_url,
                "pdf_url": pdf_url,
                "class_id": class_id,
                "district": district,
                "status": status,
                "is_pinned": is_pinned,
                "published_at": published_at,
            },
        )
        if auto_commit:
            self._db.commit()
        row = res.fetchone()
        if not row:
            raise RuntimeError("Failed to create news article.")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def get_by_id(self, news_id: str) -> Optional[dict[str, Any]]:
        """Fetch single news article with optional joined class name."""
        stmt = text(
            """
            SELECT n.*, c.name AS class_name
            FROM news_updates n
            LEFT JOIN classes c ON n.class_id = c.id
            WHERE n.id::text = :id
            """
        )
        res = self._db.execute(stmt, {"id": str(news_id)})
        row = res.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def list_news(
        self,
        *,
        status: Optional[str] = None,
        category: Optional[str] = None,
        class_id: Optional[int] = None,
        is_pinned: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List news articles with filtering and pagination."""
        where_clauses = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if status is not None:
            where_clauses.append("n.status = :status")
            params["status"] = status
        if category is not None:
            where_clauses.append("n.category = :category")
            params["category"] = category
        if class_id is not None:
            where_clauses.append("n.class_id = :class_id")
            params["class_id"] = class_id
        if is_pinned is not None:
            where_clauses.append("n.is_pinned = :is_pinned")
            params["is_pinned"] = is_pinned

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cnt_stmt = text(f"SELECT COUNT(*) FROM news_updates n {where_sql}")
        total = self._db.execute(cnt_stmt, params).scalar() or 0

        list_stmt = text(
            f"""
            SELECT n.*, c.name AS class_name
            FROM news_updates n
            LEFT JOIN classes c ON n.class_id = c.id
            {where_sql}
            ORDER BY n.is_pinned DESC, n.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        res = self._db.execute(list_stmt, params)
        rows = []
        for r in res.fetchall():
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            rows.append(d)
        return rows, total

    def update_news(
        self,
        news_id: str,
        updates: dict[str, Any],
        auto_commit: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Update fields of a news article."""
        if not updates:
            return self.get_by_id(news_id)

        sets = ["updated_at = NOW()"]
        params: dict[str, Any] = {"id": str(news_id)}

        for k, v in updates.items():
            if k in (
                "title", "summary", "content", "category", "tags",
                "thumbnail_url", "thumbnail_alt", "youtube_url", "pdf_url",
                "class_id", "district", "status", "is_pinned", "published_at"
            ):
                sets.append(f"{k} = :{k}")
                params[k] = v

        stmt = text(
            f"""
            UPDATE news_updates
            SET {", ".join(sets)}
            WHERE id::text = :id
            RETURNING *
            """
        )
        res = self._db.execute(stmt, params)
        if auto_commit:
            self._db.commit()
        row = res.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def delete_news(self, news_id: str, auto_commit: bool = True) -> bool:
        """Delete a news article by id."""
        stmt = text("DELETE FROM news_updates WHERE id::text = :id")
        res = self._db.execute(stmt, {"id": str(news_id)})
        if auto_commit:
            self._db.commit()
        return res.rowcount > 0