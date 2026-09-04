"""
Analytics telemetry and reporting endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_admin, get_current_user_optional
from app.dependencies.supabase import get_db
from app.schemas.analytics import AnalyticsDashboardResponse, AnalyticsEventCreate
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.post(
    "/event",
    status_code=status.HTTP_200_OK,
    summary="Log client usage telemetry event",
    description="Public endpoint. Accepts page_view, paper_view, download, search, like, comment events.",
)
async def log_event(
    req: AnalyticsEventCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> dict:
    """Log an analytics event."""
    service = AnalyticsService(db)
    firebase_uid = current_user.get("firebase_uid") if current_user else None
    success = service.log_event(req, firebase_uid=firebase_uid)
    return {"success": success}


@router.get(
    "/dashboard",
    response_model=AnalyticsDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get analytics dashboard metrics (Admin only)",
)
async def get_dashboard_metrics(
    period: Optional[str] = Query(None, description="Optional time period filter (today, 7d, 30d, 90d, all_time)"),
    admin_user: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AnalyticsDashboardResponse:
    """Get aggregated analytics data for today, week, month, and trends."""
    service = AnalyticsService(db)
    return service.get_dashboard_data(period=period)
