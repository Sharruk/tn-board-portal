"""
Analytics service — processes client usage telemetry and generates dashboard reports.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    AnalyticsEventCreate,
    AnalyticsPeriodStats,
    TimeSeriesPoint,
    TopItem,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service layer for usage telemetry and dashboard reporting."""

    def __init__(self, db: Session) -> None:
        self._repo = AnalyticsRepository(db)

    def log_event(self, req: AnalyticsEventCreate, firebase_uid: Optional[str] = None) -> bool:
        """Record an analytics event."""
        # Sanitize event type
        valid_events = {"page_view", "paper_view", "download", "search", "like", "comment"}
        ev_type = req.event_type.strip().lower()
        if ev_type not in valid_events:
            logger.debug("Ignoring unrecognized analytics event: %s", ev_type)
            return False

        return self._repo.insert_event(
            event_type=ev_type,
            session_id=req.session_id,
            firebase_uid=firebase_uid,
            paper_id=req.paper_id,
            class_id=req.class_id,
            subject_id=req.subject_id,
            metadata=req.metadata,
        )

    def get_dashboard_data(self, period: Optional[str] = None) -> AnalyticsDashboardResponse:
        """Generate comprehensive analytics report for admin dashboard."""
        now = datetime.now(timezone.utc)
        start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)

        today_stats = self._repo.get_period_stats(since=start_of_today)
        week_stats = self._repo.get_period_stats(since=seven_days_ago)
        month_stats = self._repo.get_period_stats(since=thirty_days_ago)
        ninety_stats = self._repo.get_period_stats(since=ninety_days_ago)
        all_time_stats = self._repo.get_period_stats(since=None)

        # Determine 'since' for top breakdown lists based on selected period
        selected_since = None
        period_key = (period or "").strip().lower()
        if period_key == "today":
            selected_since = start_of_today
        elif period_key in ("7d", "week", "this_week"):
            selected_since = seven_days_ago
        elif period_key in ("30d", "month", "this_month"):
            selected_since = thirty_days_ago
        elif period_key in ("90d", "quarter"):
            selected_since = ninety_days_ago
        elif period_key == "all_time":
            selected_since = None

        top_viewed = self._repo.get_top_viewed_papers(limit=6, since=selected_since)
        top_downloaded = self._repo.get_top_downloaded_papers(limit=6, since=selected_since)
        top_classes = self._repo.get_top_classes(limit=6, since=selected_since)
        top_subjects = self._repo.get_top_subjects(limit=6, since=selected_since)
        top_searches = self._repo.get_top_searches(limit=6, since=selected_since)

        trend_7d_raw = self._repo.get_daily_trends(days=7)
        trend_30d_raw = self._repo.get_daily_trends(days=30)
        trend_90d_raw = self._repo.get_daily_trends(days=90)

        # Select daily_trends corresponding to period
        if period_key in ("7d", "week"):
            daily_trends_raw = trend_7d_raw
        elif period_key in ("90d", "quarter"):
            daily_trends_raw = trend_90d_raw
        else:
            daily_trends_raw = trend_30d_raw

        return AnalyticsDashboardResponse(
            today=AnalyticsPeriodStats(**today_stats),
            this_week=AnalyticsPeriodStats(**week_stats),
            this_month=AnalyticsPeriodStats(**month_stats),
            all_time=AnalyticsPeriodStats(**all_time_stats),
            stat_7d=AnalyticsPeriodStats(**week_stats),
            stat_30d=AnalyticsPeriodStats(**month_stats),
            stat_90d=AnalyticsPeriodStats(**ninety_stats),
            top_viewed_papers=[TopItem(**i) for i in top_viewed],
            top_downloaded_papers=[TopItem(**i) for i in top_downloaded],
            top_classes=[TopItem(**i) for i in top_classes],
            top_subjects=[TopItem(**i) for i in top_subjects],
            top_searches=[TopItem(**i) for i in top_searches],
            daily_trends=[TimeSeriesPoint(**p) for p in daily_trends_raw],
            trend_7d=[TimeSeriesPoint(**p) for p in trend_7d_raw],
            trend_30d=[TimeSeriesPoint(**p) for p in trend_30d_raw],
            trend_90d=[TimeSeriesPoint(**p) for p in trend_90d_raw],
        )
