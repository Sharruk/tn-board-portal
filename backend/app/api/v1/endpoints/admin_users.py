"""
Admin User Management Endpoints (Admin-Only).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.schemas.admin_users import AdminUserDetailResponse, AdminUserListResponse
from app.services.admin_users_service import AdminUsersService

router = APIRouter(prefix="/admin/users", tags=["Admin Users"])


@router.get(
    "",
    response_model=AdminUserListResponse,
    summary="List registered users for Admin User Management",
)
def get_users_list(
    search: Optional[str] = Query(None, description="Search by name or email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve paginated list of registered users with submission stats and leaderboard ranks."""
    service = AdminUsersService(db)
    return service.get_users_list(search=search, limit=limit, offset=offset)


@router.get(
    "/{firebase_uid}",
    response_model=AdminUserDetailResponse,
    summary="Get user detail view with contribution history and conversations",
)
def get_user_detail(
    firebase_uid: str,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve detailed user profile, submission history, and conversations."""
    service = AdminUsersService(db)
    return service.get_user_detail(firebase_uid)
