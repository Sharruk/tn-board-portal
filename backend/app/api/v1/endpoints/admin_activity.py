"""
Admin Activity Logs Endpoints (Admin & Super Admin Only).
"""

from datetime import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.schemas.admin_activity import AdminActivityLogListResponse
from app.services.admin_activity_service import AdminActivityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/activity-logs", tags=["Admin Activity Logs"])


@router.get(
    "",
    response_model=AdminActivityLogListResponse,
    summary="List administrative activity logs (Admin & Super Admin)",
    description=(
        "Protected audit endpoint. Retrieves immutable administrative activity logs with "
        "filtering by actor_uid, action, date range, and pagination. Ordered chronologically (newest first)."
    ),
)
def get_activity_logs(
    actor_uid: Optional[str] = Query(None, description="Filter by performing administrator Firebase UID"),
    action: Optional[str] = Query(None, description="Filter by action identifier (e.g. 'admin.promote_user')"),
    start_date: Optional[datetime] = Query(None, description="Earliest timestamp (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Latest timestamp (ISO 8601)"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return (1-100)"),
    offset: int = Query(0, ge=0, description="Offset for pagination (>= 0)"),
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminActivityLogListResponse:
    """Retrieve administrative activity logs."""
    service = AdminActivityService(db)
    return service.get_activity_logs(
        actor_uid=actor_uid,
        action=action,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )