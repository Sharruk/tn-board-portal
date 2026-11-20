"""
Material Categories endpoints.
Supports public scoped category listing and administrative category management.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin, require_role
from app.dependencies.supabase import get_db
from app.schemas.material_category import (
    MaterialCategoryCreate,
    MaterialCategoryListResponse,
    MaterialCategoryOut,
    MaterialCategoryUpdate,
)
from app.services.material_categories_service import MaterialCategoriesService

router = APIRouter(tags=["Material Categories"])


# ── Public Endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/material-categories",
    response_model=MaterialCategoryListResponse,
    summary="List active material categories for a given scope",
)
def list_categories(
    class_id: Annotated[Optional[int], Query(description="Class ID (e.g. 10)")] = None,
    subject_id: Annotated[Optional[int], Query(description="Subject ID")] = None,
    db: Session = Depends(get_db),
) -> MaterialCategoryListResponse:
    """
    Returns active material categories:
    - If class_id and subject_id are provided: returns Global + Class + Subject categories.
    - If only class_id is provided: returns Global + Class categories.
    - If neither: returns all active categories.
    """
    service = MaterialCategoriesService(db)
    return service.list_categories(class_id=class_id, subject_id=subject_id, active_only=True)


# ── Admin Endpoints ───────────────────────────────────────────────────────────

@router.get(
    "/admin/material-categories",
    response_model=MaterialCategoryListResponse,
    summary="List all categories including inactive (Admin)",
)
def list_all_categories_admin(
    class_id: Annotated[Optional[int], Query()] = None,
    subject_id: Annotated[Optional[int], Query()] = None,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MaterialCategoryListResponse:
    service = MaterialCategoriesService(db)
    return service.list_categories(class_id=class_id, subject_id=subject_id, active_only=False)


@router.post(
    "/admin/material-categories",
    response_model=MaterialCategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a dynamic material category (Admin)",
)
def create_category(
    payload: MaterialCategoryCreate,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MaterialCategoryOut:
    service = MaterialCategoriesService(db)
    return service.create_category(payload)


@router.put(
    "/admin/material-categories/{category_id}",
    response_model=MaterialCategoryOut,
    summary="Update or archive a category (Admin)",
)
def update_category(
    category_id: int,
    payload: MaterialCategoryUpdate,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MaterialCategoryOut:
    service = MaterialCategoriesService(db)
    return service.update_category(category_id, payload)


@router.delete(
    "/admin/material-categories/{category_id}",
    summary="Delete or archive category (Admin)",
)
def delete_category(
    category_id: int,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = MaterialCategoriesService(db)
    return service.delete_or_archive_category(category_id)


@router.patch(
    "/admin/material-categories/{category_id}/reactivate",
    response_model=MaterialCategoryOut,
    summary="Reactivate an archived category (Admin)",
)
def reactivate_category(
    category_id: int,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MaterialCategoryOut:
    service = MaterialCategoriesService(db)
    return service.reactivate_category(category_id)
