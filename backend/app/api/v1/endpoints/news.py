"""
News & Updates endpoints.

Provides public endpoints for browsing news/articles and admin endpoints
for creating, updating, and deleting news with centralized audit logging
and transactional outbox side-effects.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user_optional, require_admin
from app.dependencies.supabase import get_db
from app.schemas.news import (
    NewsCreate,
    NewsDeleteResponse,
    NewsListResponse,
    NewsOut,
    NewsUpdate,
)
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["News & Updates"])


# ── GET /api/v1/news ──────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=NewsListResponse,
    summary="List news articles",
    description="Public endpoint. Returns news articles with optional category, status, and class filtering.",
)
async def list_news(
    status_filter: Annotated[Optional[str], Query(alias="status", description="Filter by status ('published', 'draft', 'archived')")] = None,
    category: Annotated[Optional[str], Query(description="Filter by category")] = None,
    class_id: Annotated[Optional[int], Query(description="Filter by class ID")] = None,
    is_pinned: Annotated[Optional[bool], Query(description="Filter by pinned status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    db: Session = Depends(get_db),
) -> NewsListResponse:
    """List news articles with filtering."""
    service = NewsService(db)
    return service.list_news(
        status=status_filter,
        category=category,
        class_id=class_id,
        is_pinned=is_pinned,
        limit=limit,
        offset=offset,
    )


# ── GET /api/v1/news/{news_id} ────────────────────────────────────────────────

@router.get(
    "/{news_id}",
    response_model=NewsOut,
    summary="Get news article details",
    description="Public endpoint. Retrieve details of a specific news article by ID or slug.",
)
async def get_news(
    news_id: str,
    db: Session = Depends(get_db),
) -> NewsOut:
    """Get single news article."""
    service = NewsService(db)
    return service.get_news(news_id)


# ── POST /api/v1/news ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=NewsOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create news article (admin)",
    description="Admin only. Creates a news article with centralized audit logging.",
)
async def create_news(
    req: NewsCreate,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NewsOut:
    """Create a new news article."""
    client_ip = request.client.host if request.client else None
    service = NewsService(db)
    return service.create_news(req=req, current_user=current_user, ip_address=client_ip)


# ── PATCH /api/v1/news/{news_id} ──────────────────────────────────────────────

@router.patch(
    "/{news_id}",
    response_model=NewsOut,
    summary="Update news article (admin)",
    description="Admin only. Updates a news article with centralized audit logging.",
)
async def update_news(
    news_id: str,
    req: NewsUpdate,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NewsOut:
    """Update an existing news article."""
    client_ip = request.client.host if request.client else None
    service = NewsService(db)
    return service.update_news(
        news_id=news_id,
        req=req,
        current_user=current_user,
        ip_address=client_ip,
    )


# ── DELETE /api/v1/news/{news_id} ─────────────────────────────────────────────

@router.delete(
    "/{news_id}",
    response_model=NewsDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete news article (admin)",
    description="Admin only. Deletes article, queues media storage cleanup into outbox, and logs audit event atomically.",
)
async def delete_news(
    news_id: str,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NewsDeleteResponse:
    """Delete a news article."""
    client_ip = request.client.host if request.client else None
    service = NewsService(db)
    return service.delete_news(
        news_id=news_id,
        current_user=current_user,
        ip_address=client_ip,
    )