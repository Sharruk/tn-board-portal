"""
Pydantic schemas for Analytics Telemetry and Dashboard reporting.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class AnalyticsEventCreate(BaseModel):
    """Payload for logging a client usage event."""

    event_type: str = Field(..., description="Event type: 'page_view', 'paper_view', 'download', 'search', 'like', 'comment'")
    session_id: Optional[str] = Field(None, description="Anonymous session identifier")
    paper_id: Optional[int] = Field(None, description="Related paper ID")
    class_id: Optional[int] = Field(None, description="Related class ID")
    subject_id: Optional[int] = Field(None, description="Related subject ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Safe metadata like search query, page path")


class AnalyticsPeriodStats(BaseModel):
    """Aggregated stats for a specific timeframe."""

    visitors: int = 0
    page_views: int = 0
    paper_views: int = 0
    downloads: int = 0
    searches: int = 0
    likes: int = 0
    comments: int = 0


class TopItem(BaseModel):
    """Top ranking item in analytics."""

    id: Optional[Any] = None
    name: str
    count: int
    extra: Optional[str] = None


class TimeSeriesPoint(BaseModel):
    """Daily or hourly trend data point."""

    date: str
    visitors: int = 0
    page_views: int = 0
    paper_views: int = 0
    downloads: int = 0


class AnalyticsDashboardResponse(BaseModel):
    """Admin analytics dashboard report."""

    today: AnalyticsPeriodStats
    this_week: AnalyticsPeriodStats
    this_month: AnalyticsPeriodStats
    all_time: AnalyticsPeriodStats

    top_viewed_papers: list[TopItem] = Field(default_factory=list)
    top_downloaded_papers: list[TopItem] = Field(default_factory=list)
    top_classes: list[TopItem] = Field(default_factory=list)
    top_subjects: list[TopItem] = Field(default_factory=list)
    top_searches: list[TopItem] = Field(default_factory=list)

    trend_7d: list[TimeSeriesPoint] = Field(default_factory=list)
    trend_30d: list[TimeSeriesPoint] = Field(default_factory=list)
    trend_90d: list[TimeSeriesPoint] = Field(default_factory=list)
