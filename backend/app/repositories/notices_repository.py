"""
Official Notices repository — direct PostgreSQL access for the official_notices table.
"""

import logging
from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NoticesRepository:
    """Data access layer for official_notices."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_notice(
        self,
        *,
        title: str,
        category: str,
        year: int,
        description: Optional[str] = None,
        class_id: Optional[int] = None,
        file_path: Optional[str] = None,
        public_url: Optional[str] = None,
        file_type: Optional[str] = None,
        youtube_url: Optional[str] = None,
        is_visible: bool = True,
        is_pinned: bool = False,
        expires_at: Optional[Any] = None,
        auto_commit: bool = True,
    ) -> dict[str, Any]:
        """Insert a new official notice."""
        stmt = text(
            """
            INSERT INTO official_notices (
                title, category, class_id, year, description, file_path,
                public_url, file_type, youtube_url, is_visible, is_pinned,
                expires_at, view_count, download_count, created_at, updated_at
            )
            VALUES (
                :title, :category, :class_id, :year, :description, :file_path,
                :public_url, :file_type, :youtube_url, :is_visible, :is_pinned,
                :expires_at, 0, 0, NOW(), NOW()
            )
            RETURNING id, title, category, class_id, year, description, file_path,
                      public_url, file_type, youtube_url, is_visible, is_pinned,
                      expires_at, view_count, download_count, created_at, updated_at
            """
        )
        res = self._db.execute(
            stmt,
            {
                "title": title.strip(),
                "category": category.strip(),
                "class_id": class_id,
                "year": year,
                "description": description.strip() if description else None,
                "file_path": file_path,
                "public_url": public_url,
                "file_type": file_type,
                "youtube_url": youtube_url,
                "is_visible": is_visible,
                "is_pinned": is_pinned,
                "expires_at": expires_at,
            },
        )
        if auto_commit:
            self._db.commit()
        row = res.fetchone()
        if not row:
            raise RuntimeError("Failed to create official notice.")
        d = dict(row._mapping)
        return d

    def get_by_id(self, notice_id: int) -> Optional[dict[str, Any]]:
        """Fetch single notice with optional joined class name."""
        stmt = text(
            """
            SELECT n.*, c.name AS class_name
            FROM official_notices n
            LEFT JOIN classes c ON n.class_id = c.id
            WHERE n.id = :id
            """
        )
        res = self._db.execute(stmt, {"id": notice_id})
        row = res.fetchone()
        return dict(row._mapping) if row else None

    def list_notices(
        self,
        *,
        category: Optional[str] = None,
        class_id: Optional[int] = None,
        year: Optional[int] = None,
        is_visible: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List official notices with filtering and pagination."""
        where_clauses = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if category is not None:
            where_clauses.append("n.category = :category")
            params["category"] = category
        if class_id is not None:
            where_clauses.append("n.class_id = :class_id")
            params["class_id"] = class_id
        if year is not None:
            where_clauses.append("n.year = :year")
            params["year"] = year
        if is_visible is not None:
            where_clauses.append("n.is_visible = :is_visible")
            params["is_visible"] = is_visible

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        cnt_stmt = text(f"SELECT COUNT(*) FROM official_notices n {where_sql}")
        total = self._db.execute(cnt_stmt, params).scalar() or 0

        list_stmt = text(
            f"""
            SELECT n.*, c.name AS class_name
            FROM official_notices n
            LEFT JOIN classes c ON n.class_id = c.id
            {where_sql}
            ORDER BY n.is_pinned DESC, n.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        res = self._db.execute(list_stmt, params)
        rows = [dict(r._mapping) for r in res.fetchall()]
        return rows, total

    def update_notice(
        self,
        notice_id: int,
        updates: dict[str, Any],
        auto_commit: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Update fields of an official notice."""
        if not updates:
            return self.get_by_id(notice_id)

        sets = ["updated_at = NOW()"]
        params: dict[str, Any] = {"id": notice_id}

        for k, v in updates.items():
            if k in (
                "title", "category", "class_id", "year", "description",
                "file_path", "public_url", "file_type", "youtube_url",
                "is_visible", "is_pinned", "expires_at"
            ):
                sets.append(f"{k} = :{k}")
                params[k] = v

        stmt = text(
            f"""
            UPDATE official_notices
            SET {", ".join(sets)}
            WHERE id = :id
            RETURNING *
            """
        )
        res = self._db.execute(stmt, params)
        if auto_commit:
            self._db.commit()
        row = res.fetchone()
        return dict(row._mapping) if row else None

    def delete_notice(self, notice_id: int, auto_commit: bool = True) -> bool:
        """Delete an official notice by id."""
        stmt = text("DELETE FROM official_notices WHERE id = :id")
        res = self._db.execute(stmt, {"id": notice_id})
        if auto_commit:
            self._db.commit()
        return res.rowcount > 0