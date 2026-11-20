"""
Material Categories repository — PostgreSQL data access for material_categories table.
Handles hybrid scoped categories (Global, Class-level, Subject-level).
"""

import logging
import re
import uuid
from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _slugify(text_val: str) -> str:
    """Generate a clean URL-safe slug."""
    s = text_val.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s[:100] or "category"


class MaterialCategoriesRepository:
    """Data access layer for material_categories."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, category_id: int) -> Optional[dict[str, Any]]:
        """Retrieve single category with joined class and subject names."""
        stmt = text(
            """
            SELECT 
                mc.id, mc.class_id, mc.subject_id, mc.name, mc.slug, 
                mc.description, mc.is_active, mc.display_order, 
                mc.created_at, mc.updated_at,
                c.name AS class_name,
                s.name AS subject_name,
                (
                    SELECT COUNT(*)::int 
                    FROM study_materials sm 
                    WHERE sm.category_id = mc.id
                ) AS material_count
            FROM material_categories mc
            LEFT JOIN classes c ON mc.class_id = c.id
            LEFT JOIN subjects s ON mc.subject_id = s.id
            WHERE mc.id = :id
            """
        )
        row = self._db.execute(stmt, {"id": category_id}).fetchone()
        return dict(row._mapping) if row else None

    def get_by_slug(self, slug: str, class_id: Optional[int] = None, subject_id: Optional[int] = None) -> Optional[dict[str, Any]]:
        """Retrieve category by slug within a specific scope."""
        conditions = ["mc.slug = :slug"]
        params: dict[str, Any] = {"slug": slug}

        if class_id is None:
            conditions.append("mc.class_id IS NULL")
        else:
            conditions.append("mc.class_id = :class_id")
            params["class_id"] = class_id

        if subject_id is None:
            conditions.append("mc.subject_id IS NULL")
        else:
            conditions.append("mc.subject_id = :subject_id")
            params["subject_id"] = subject_id

        where_clause = " AND ".join(conditions)
        stmt = text(
            f"""
            SELECT 
                mc.id, mc.class_id, mc.subject_id, mc.name, mc.slug, 
                mc.description, mc.is_active, mc.display_order, 
                mc.created_at, mc.updated_at
            FROM material_categories mc
            WHERE {where_clause}
            """
        )
        row = self._db.execute(stmt, params).fetchone()
        return dict(row._mapping) if row else None

    def list_categories(
        self,
        *,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """
        List categories applicable to a given scope:
        - If class_id and subject_id provided: returns Global + Class + Subject categories.
        - If only class_id provided: returns Global + Class categories (no subject-scoped).
        - If neither provided: returns all categories.
        """
        params: dict[str, Any] = {}
        conditions = []

        if active_only:
            conditions.append("mc.is_active = true")

        if class_id is not None and subject_id is not None:
            conditions.append(
                """
                (
                    (mc.class_id IS NULL AND mc.subject_id IS NULL) OR
                    (mc.class_id = :class_id AND mc.subject_id IS NULL) OR
                    (mc.class_id = :class_id AND mc.subject_id = :subject_id)
                )
                """
            )
            params["class_id"] = class_id
            params["subject_id"] = subject_id
        elif class_id is not None:
            conditions.append(
                """
                (
                    (mc.class_id IS NULL AND mc.subject_id IS NULL) OR
                    (mc.class_id = :class_id AND mc.subject_id IS NULL)
                )
                """
            )
            params["class_id"] = class_id
        elif subject_id is not None:
            conditions.append(
                """
                (
                    (mc.class_id IS NULL AND mc.subject_id IS NULL) OR
                    (mc.subject_id = :subject_id)
                )
                """
            )
            params["subject_id"] = subject_id

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        stmt = text(
            f"""
            SELECT 
                mc.id, mc.class_id, mc.subject_id, mc.name, mc.slug, 
                mc.description, mc.is_active, mc.display_order, 
                mc.created_at, mc.updated_at,
                c.name AS class_name,
                s.name AS subject_name,
                (
                    SELECT COUNT(*)::int 
                    FROM study_materials sm 
                    WHERE sm.category_id = mc.id
                ) AS material_count
            FROM material_categories mc
            LEFT JOIN classes c ON mc.class_id = c.id
            LEFT JOIN subjects s ON mc.subject_id = s.id
            {where_clause}
            ORDER BY mc.display_order ASC, mc.name ASC
            """
        )
        rows = self._db.execute(stmt, params).fetchall()
        return [dict(r._mapping) for r in rows]

    def get_by_name(
        self,
        name: str,
        *,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """Find category by case-insensitive name within the given scope."""
        conditions = ["LOWER(TRIM(name)) = LOWER(TRIM(:name))"]
        params: dict[str, Any] = {"name": name}

        if class_id is None:
            conditions.append("class_id IS NULL")
        else:
            conditions.append("class_id = :class_id")
            params["class_id"] = class_id

        if subject_id is None:
            conditions.append("subject_id IS NULL")
        else:
            conditions.append("subject_id = :subject_id")
            params["subject_id"] = subject_id

        stmt = text(f"SELECT * FROM material_categories WHERE {' AND '.join(conditions)} LIMIT 1")
        row = self._db.execute(stmt, params).fetchone()
        return dict(row._mapping) if row else None

    def create_category(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        display_order: int = 0,
        is_active: bool = True,
        slug: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new hybrid category with unique name and slug within scope."""
        from app.utils.exceptions import ValidationError

        # 1. Enforce name uniqueness within scope
        existing = self.get_by_name(name, class_id=class_id, subject_id=subject_id)
        if existing:
            if existing.get("is_active"):
                raise ValidationError(f"A category named '{name}' already exists for this scope.")
            else:
                # Reactivate previously archived category rather than creating a duplicate
                updated = self.update_category(
                    existing["id"],
                    name=name,
                    description=description,
                    display_order=display_order,
                    is_active=True,
                )
                if updated:
                    return updated
                return existing

        # 2. Enforce slug uniqueness within scope (without random-suffix generation)
        base_slug = slug or _slugify(name)
        if not base_slug:
            base_slug = "category"
        chk = self.get_by_slug(base_slug, class_id=class_id, subject_id=subject_id)
        if chk:
            if chk.get("is_active"):
                raise ValidationError(f"A category with slug '{base_slug}' already exists for this scope.")
            else:
                updated = self.update_category(
                    chk["id"],
                    name=name,
                    description=description,
                    display_order=display_order,
                    is_active=True,
                )
                if updated:
                    return updated
                return chk

        stmt = text(
            """
            INSERT INTO material_categories (
                class_id, subject_id, name, slug, description, is_active, display_order, created_at, updated_at
            )
            VALUES (
                :class_id, :subject_id, :name, :slug, :description, :is_active, :display_order, NOW(), NOW()
            )
            RETURNING id, class_id, subject_id, name, slug, description, is_active, display_order, created_at, updated_at
            """
        )
        row = self._db.execute(
            stmt,
            {
                "class_id": class_id,
                "subject_id": subject_id,
                "name": name,
                "slug": base_slug,
                "description": description,
                "is_active": is_active,
                "display_order": display_order,
            },
        ).fetchone()
        self._db.commit()
        return dict(row._mapping)

    def update_category(
        self,
        category_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        display_order: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[dict[str, Any]]:
        """Update category fields."""
        fields = ["updated_at = NOW()"]
        params: dict[str, Any] = {"id": category_id}

        if name is not None:
            fields.append("name = :name")
            params["name"] = name
        if description is not None:
            fields.append("description = :description")
            params["description"] = description
        if display_order is not None:
            fields.append("display_order = :display_order")
            params["display_order"] = display_order
        if is_active is not None:
            fields.append("is_active = :is_active")
            params["is_active"] = is_active

        stmt = text(
            f"""
            UPDATE material_categories
            SET {', '.join(fields)}
            WHERE id = :id
            RETURNING id, class_id, subject_id, name, slug, description, is_active, display_order, created_at, updated_at
            """
        )
        row = self._db.execute(stmt, params).fetchone()
        self._db.commit()
        return dict(row._mapping) if row else None

    def count_materials(self, category_id: int) -> int:
        """Count materials attached to this category (any status)."""
        stmt = text("SELECT COUNT(*)::int FROM study_materials WHERE category_id = :id")
        return self._db.execute(stmt, {"id": category_id}).scalar() or 0

    def delete_category(self, category_id: int) -> dict[str, Any]:
        """
        Soft-archive if materials reference this category;
        hard-delete only if 0 materials reference it.
        """
        mat_count = self.count_materials(category_id)
        if mat_count > 0:
            self.update_category(category_id, is_active=False)
            return {
                "id": category_id,
                "deleted": False,
                "archived": True,
                "message": f"Category is referenced by {mat_count} materials. It was archived instead of deleted.",
            }

        stmt = text("DELETE FROM material_categories WHERE id = :id RETURNING id")
        self._db.execute(stmt, {"id": category_id})
        self._db.commit()
        return {
            "id": category_id,
            "deleted": True,
            "archived": False,
            "message": "Category deleted successfully.",
        }

    def reactivate_category(self, category_id: int) -> Optional[dict[str, Any]]:
        """Reactivate an archived category."""
        return self.update_category(category_id, is_active=True)
