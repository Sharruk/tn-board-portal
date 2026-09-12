"""
Admin Activity endpoints (Admin-Only).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.schemas.admin_activity import AdminActivityListResponse
from app.services.admin_activity_service import AdminActivityService

router = APIRouter(prefix="/admin/activity", tags=["Admin Activity"])


@router.get(
    "",
    response_model=AdminActivityListResponse,
    summary="List administrative platform actions (Admin & Super Admin)",
    description="Returns paginated immutable audit logs of administrative actions.",
)
def get_activity_feed(
    action: Optional[str] = Query(None, description="Filter by action type"),
    target_type: Optional[str] = Query(None, description="Filter by target type: paper, user, submission, report"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve immutable admin activity history."""
    service = AdminActivityService(db)
    return service.list_activities(
        limit=limit,
        offset=offset,
        action=action,
        target_type=target_type,
    )
