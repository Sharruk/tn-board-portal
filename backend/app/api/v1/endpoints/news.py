"""
News & Updates endpoints.

Provides public endpoints for browsing news/articles and admin endpoints
for creating, updating, and deleting news with centralized audit logging
and transactional outbox side-effects.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
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
from app.services.storage_upload_service import (
    NEWS_ALLOWED_EXTENSIONS,
    NEWS_BUCKET,
    NEWS_MAX_SIZE_BYTES,
    cleanup_storage_file,
    validate_and_upload_file,
)
from app.utils.exceptions import BadRequestError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["News & Updates"])


# ── GET /api/v1/news ──────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=NewsListResponse,
    summary="List published news articles (public)",
    description="Public endpoint. Returns only published news articles whose published_at <= NOW(). Draft and archived articles are never returned.",
)
async def list_news(
    category: Annotated[Optional[str], Query(description="Filter by category")] = None,
    class_id: Annotated[Optional[int], Query(description="Filter by class ID")] = None,
    is_pinned: Annotated[Optional[bool], Query(description="Filter by pinned status")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    db: Session = Depends(get_db),
) -> NewsListResponse:
    """Public listing of published news articles."""
    service = NewsService(db)
    return service.list_news(
        category=category,
        class_id=class_id,
        is_pinned=is_pinned,
        limit=limit,
        offset=offset,
        published_only=True,
    )


# ── GET /api/v1/news/admin ────────────────────────────────────────────────────

@router.get(
    "/admin",
    response_model=NewsListResponse,
    summary="List all news articles (admin)",
    description="Admin only. Returns news articles across all statuses (published, archived, draft) with optional filtering.",
)
async def list_admin_news(
    status_filter: Annotated[Optional[str], Query(alias="status", description="Filter by status ('published', 'draft', 'archived')")] = None,
    category: Annotated[Optional[str], Query(description="Filter by category")] = None,
    class_id: Annotated[Optional[int], Query(description="Filter by class ID")] = None,
    is_pinned: Annotated[Optional[bool], Query(description="Filter by pinned status")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NewsListResponse:
    """List news articles for admin management with full status access."""
    service = NewsService(db)
    return service.list_news(
        status=status_filter,
        category=category,
        class_id=class_id,
        is_pinned=is_pinned,
        limit=limit,
        offset=offset,
        published_only=False,
    )


# ── GET /api/v1/news/{news_id} ────────────────────────────────────────────────

@router.get(
    "/{news_id}",
    response_model=NewsOut,
    summary="Get news article details",
    description="Retrieve details of a specific news article by ID or slug. Draft and archived articles require admin authorization.",
)
async def get_news(
    news_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> NewsOut:
    """Get single news article. Public callers only receive published articles."""
    is_admin = bool(current_user and current_user.get("role") == "ADMIN")
    service = NewsService(db)
    return service.get_news(news_id, allow_non_published=is_admin)


# ── POST /api/v1/news/upload ──────────────────────────────────────────────────

@router.post(
    "/upload",
    summary="Upload news media file (admin)",
    description="Admin only. Uploads a thumbnail image or PDF to the news-media bucket using the server-side storage client.",
)
async def upload_news_media(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
) -> dict:
    """Upload a news media file (image or PDF) securely via server-side Supabase Storage."""
    storage_path, public_url, file_type = await validate_and_upload_file(
        file=file,
        bucket=NEWS_BUCKET,
        allowed_extensions=NEWS_ALLOWED_EXTENSIONS,
        max_size_bytes=NEWS_MAX_SIZE_BYTES,
    )
    return {
        "public_url": public_url,
        "publicUrl": public_url,
        "file_path": storage_path,
        "filename": storage_path,
        "file_type": file_type,
    }


# ── DELETE /api/v1/news/media ─────────────────────────────────────────────────

@router.delete(
    "/media",
    summary="Delete news media file (admin)",
    description="Admin only. Removes a media file from the news-media bucket during replacement or cleanup.",
)
async def delete_news_media(
    url: Optional[str] = Query(None, description="Public URL of the media"),
    path: Optional[str] = Query(None, description="Storage path of the media"),
    current_user: dict = Depends(require_admin),
) -> dict:
    """Delete a media file from news-media bucket."""
    file_path = path
    if not file_path and url:
        if "/news-media/" in url:
            file_path = url.split("/news-media/")[-1].split("?")[0]
        else:
            file_path = url.rsplit("/", 1)[-1].split("?")[0]
    if file_path:
        cleanup_storage_file(NEWS_BUCKET, file_path)
    return {"message": "Media cleanup processed"}


# ── POST /api/v1/news ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=NewsOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create news article (admin)",
    description="Admin only. Creates a news article with centralized audit logging and secure server-side storage upload.",
)
async def create_news(
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NewsOut:
    """Create a new news article via JSON or multipart/form-data."""
    client_ip = request.client.host if request.client else None
    service = NewsService(db)
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        body = await request.json()
        req = NewsCreate(**body)
        return service.create_news(req=req, current_user=current_user, ip_address=client_ip)

    if content_type.startswith("multipart/form-data") or content_type.startswith("application/x-www-form-urlencoded"):
        form = await request.form()
        title = str(form.get("title", "")).strip()
        if not title:
            raise BadRequestError("Title is required.")

        category = str(form.get("category", "")).strip()
        if not category:
            raise BadRequestError("Category is required.")

        summary = str(form.get("summary", "")).strip() or None
        content = str(form.get("content", "")).strip() or None
        thumbnail_alt = str(form.get("thumbnail_alt", "")).strip() or None
        youtube_url = str(form.get("youtube_url", "")).strip() or None
        district = str(form.get("district", "")).strip() or None

        class_id_raw = form.get("class_id")
        class_id = int(class_id_raw) if class_id_raw and str(class_id_raw).isdigit() else None

        status_raw = form.get("status", "draft")
        article_status = str(status_raw).strip() if status_raw else "draft"
        if article_status not in ("draft", "published", "archived"):
            article_status = "draft"

        is_pinned_raw = form.get("is_pinned", "false")
        is_pinned = str(is_pinned_raw).lower() in ("true", "1")

        published_at_raw = form.get("published_at")
        published_at = str(published_at_raw).strip() or None

        tags_raw = form.get("tags")
        if isinstance(tags_raw, str):
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        elif isinstance(tags_raw, list):
            tags = [str(t).strip() for t in tags_raw if str(t).strip()]
        else:
            tags = []

        thumbnail_url = str(form.get("thumbnail_url", "")).strip() or None
        pdf_url = str(form.get("pdf_url", "")).strip() or None
        uploaded_paths: list[str] = []

        # Handle direct file attachments in multipart form if present
        thumbnail_file = form.get("thumbnail")
        if thumbnail_file and hasattr(thumbnail_file, "filename") and thumbnail_file.filename:
            storage_path, t_url, _ = await validate_and_upload_file(
                file=thumbnail_file,
                bucket=NEWS_BUCKET,
                allowed_extensions=NEWS_ALLOWED_EXTENSIONS,
                max_size_bytes=NEWS_MAX_SIZE_BYTES,
            )
            thumbnail_url = t_url
            uploaded_paths.append(storage_path)

        pdf_file = form.get("pdf")
        if pdf_file and hasattr(pdf_file, "filename") and pdf_file.filename:
            storage_path, p_url, _ = await validate_and_upload_file(
                file=pdf_file,
                bucket=NEWS_BUCKET,
                allowed_extensions={"pdf"},
                max_size_bytes=NEWS_MAX_SIZE_BYTES,
            )
            pdf_url = p_url
            uploaded_paths.append(storage_path)

        req = NewsCreate(
            title=title,
            category=category,
            summary=summary,
            content=content,
            tags=tags,
            thumbnail_url=thumbnail_url,
            thumbnail_alt=thumbnail_alt,
            youtube_url=youtube_url,
            pdf_url=pdf_url,
            class_id=class_id,
            district=district,
            status=article_status,
            is_pinned=is_pinned,
            published_at=published_at,
        )

        try:
            return service.create_news(req=req, current_user=current_user, ip_address=client_ip)
        except Exception:
            for p in uploaded_paths:
                cleanup_storage_file(NEWS_BUCKET, p)
            raise

    raise BadRequestError("Unsupported Content-Type. Expected application/json or multipart/form-data.")


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


# ── POST /api/v1/news/{news_id}/archive ───────────────────────────────────────

@router.post(
    "/{news_id}/archive",
    response_model=NewsOut,
    summary="Archive news article (admin)",
    description="Admin only. Sets article status to 'archived' with centralized audit logging.",
)
async def archive_news(
    news_id: str,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NewsOut:
    """Archive a news article."""
    client_ip = request.client.host if request.client else None
    service = NewsService(db)
    return service.update_news(
        news_id=news_id,
        req=NewsUpdate(status="archived"),
        current_user=current_user,
        ip_address=client_ip,
    )


# ── POST /api/v1/news/{news_id}/unarchive ─────────────────────────────────────

@router.post(
    "/{news_id}/unarchive",
    response_model=NewsOut,
    summary="Unarchive news article (admin)",
    description="Admin only. Restores article status to 'published' with centralized audit logging.",
)
async def unarchive_news(
    news_id: str,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NewsOut:
    """Unarchive / restore a news article to published status."""
    client_ip = request.client.host if request.client else None
    service = NewsService(db)
    return service.update_news(
        news_id=news_id,
        req=NewsUpdate(status="published"),
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