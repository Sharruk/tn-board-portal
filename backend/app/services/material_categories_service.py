"""
Material Categories service — business logic and validation for material categories.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.repositories.classes_repository import ClassesRepository
from app.repositories.material_categories_repository import MaterialCategoriesRepository
from app.repositories.subjects_repository import SubjectsRepository
from app.schemas.material_category import (
    MaterialCategoryCreate,
    MaterialCategoryListResponse,
    MaterialCategoryOut,
    MaterialCategoryUpdate,
)
from app.utils.exceptions import BadRequestError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class MaterialCategoriesService:
    """Service layer for material categories."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = MaterialCategoriesRepository(db)
        self._classes_repo = ClassesRepository(db)
        self._subjects_repo = SubjectsRepository(db)

    def get_category(self, category_id: int) -> MaterialCategoryOut:
        cat = self._repo.get_by_id(category_id)
        if not cat:
            raise NotFoundError("MaterialCategory", category_id)
        return MaterialCategoryOut(**cat)

    def list_categories(
        self,
        *,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        active_only: bool = True,
    ) -> MaterialCategoryListResponse:
        rows = self._repo.list_categories(
            class_id=class_id,
            subject_id=subject_id,
            active_only=active_only,
        )
        return MaterialCategoryListResponse(
            data=[MaterialCategoryOut(**r) for r in rows],
            total=len(rows),
        )

    def create_category(self, payload: MaterialCategoryCreate) -> MaterialCategoryOut:
        # Validate scope consistency
        if payload.class_id is None and payload.subject_id is not None:
            raise ValidationError("A subject-scoped category cannot exist without a parent class.")

        if payload.class_id is not None:
            cls_row = self._classes_repo.get_by_id(payload.class_id)
            if not cls_row:
                raise ValidationError(f"Class id {payload.class_id} does not exist.")

        if payload.subject_id is not None:
            subj_row = self._subjects_repo.get_by_id(payload.subject_id)
            if not subj_row:
                raise ValidationError(f"Subject id {payload.subject_id} does not exist.")
            if subj_row.get("class_id") != payload.class_id:
                raise ValidationError(f"Subject id {payload.subject_id} does not belong to class {payload.class_id}.")

        created = self._repo.create_category(
            name=payload.name,
            description=payload.description,
            class_id=payload.class_id,
            subject_id=payload.subject_id,
            display_order=payload.display_order,
            is_active=payload.is_active,
            slug=payload.slug,
        )
        return self.get_category(created["id"])

    def update_category(self, category_id: int, payload: MaterialCategoryUpdate) -> MaterialCategoryOut:
        existing = self._repo.get_by_id(category_id)
        if not existing:
            raise NotFoundError("MaterialCategory", category_id)

        updated = self._repo.update_category(
            category_id,
            name=payload.name,
            description=payload.description,
            display_order=payload.display_order,
            is_active=payload.is_active,
        )
        return self.get_category(category_id)

    def delete_or_archive_category(self, category_id: int) -> dict[str, Any]:
        existing = self._repo.get_by_id(category_id)
        if not existing:
            raise NotFoundError("MaterialCategory", category_id)
        return self._repo.delete_category(category_id)

    def reactivate_category(self, category_id: int) -> MaterialCategoryOut:
        existing = self._repo.get_by_id(category_id)
        if not existing:
            raise NotFoundError("MaterialCategory", category_id)
        self._repo.reactivate_category(category_id)
        return self.get_category(category_id)
