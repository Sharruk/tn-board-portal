"""
Official Notices endpoints.

Provides public endpoints for browsing official notices and admin endpoints
for managing notices with centralized audit logging and transactional outbox.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user_optional, require_admin
from app.dependencies.supabase import get_db
from app.schemas.notice import (
    NoticeCreate,
    NoticeDeleteResponse,
    NoticeListResponse,
    NoticeOut,
    NoticeUpdate,
)
from app.services.notices_service import NoticesService
from app.services.storage_upload_service import (
    NOTICES_ALLOWED_EXTENSIONS,
    NOTICES_BUCKET,
    NOTICES_MAX_SIZE_BYTES,
    cleanup_storage_file,
    validate_and_upload_file,
)
from app.utils.exceptions import BadRequestError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notices", tags=["Official Notices"])


# ── GET /api/v1/notices ────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=NoticeListResponse,
    summary="List official notices",
    description="Public endpoint. Returns official notices with optional category, class, and year filtering.",
)
async def list_notices(
    category: Annotated[Optional[str], Query(description="Filter by category")] = None,
    class_id: Annotated[Optional[int], Query(description="Filter by class ID")] = None,
    year: Annotated[Optional[int], Query(description="Filter by academic year")] = None,
    is_visible: Annotated[Optional[bool], Query(description="Filter by visibility")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
    db: Session = Depends(get_db),
) -> NoticeListResponse:
    """List official notices with filtering."""
    service = NoticesService(db)
    return service.list_notices(
        category=category,
        class_id=class_id,
        year=year,
        is_visible=is_visible,
        limit=limit,
        offset=offset,
    )


# ── GET /api/v1/notices/{notice_id} ───────────────────────────────────────────

@router.get(
    "/{notice_id}",
    response_model=NoticeOut,
    summary="Get official notice details",
    description="Public endpoint. Retrieve details of a specific official notice.",
)
async def get_notice(
    notice_id: int,
    db: Session = Depends(get_db),
) -> NoticeOut:
    """Get single official notice."""
    service = NoticesService(db)
    return service.get_notice(notice_id)


# ── POST /api/v1/notices ──────────────────────────────────────────────────────

@router.post(
    "",
    response_model=NoticeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create official notice (admin)",
    description="Admin only. Creates an official notice with centralized audit logging and secure server-side storage upload.",
)
async def create_notice(
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NoticeOut:
    """Create a new official notice via JSON or multipart/form-data."""
    client_ip = request.client.host if request.client else None
    service = NoticesService(db)
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        body = await request.json()
        req = NoticeCreate(**body)
        return service.create_notice(req=req, current_user=current_user, ip_address=client_ip)

    if content_type.startswith("multipart/form-data") or content_type.startswith("application/x-www-form-urlencoded"):
        form = await request.form()
        title = str(form.get("title", "")).strip()
        if not title:
            raise BadRequestError("Title is required.")

        category = str(form.get("category", "")).strip()
        if not category:
            raise BadRequestError("Category is required.")

        year_raw = form.get("year")
        try:
            year = int(year_raw) if year_raw is not None else None
        except (ValueError, TypeError):
            raise BadRequestError("Year must be a valid integer.")
        if year is None:
            raise BadRequestError("Year is required.")

        class_id_raw = form.get("class_id")
        class_id = int(class_id_raw) if class_id_raw and str(class_id_raw).isdigit() else None
        description = str(form.get("description", "")).strip() or None
        youtube_url = str(form.get("youtube_url", "")).strip() or None
        expires_at_raw = str(form.get("expires_at", "")).strip() or None

        is_visible_raw = form.get("is_visible")
        if is_visible_raw is not None:
            is_visible = str(is_visible_raw).lower() in ("true", "1")
        else:
            is_visible = True

        is_pinned_raw = form.get("is_pinned", "false")
        is_pinned = str(is_pinned_raw).lower() in ("true", "1")

        file_obj = form.get("file")
        storage_path = None
        public_url = None
        file_type = None

        if file_obj and hasattr(file_obj, "filename") and file_obj.filename:
            storage_path, public_url, file_type = await validate_and_upload_file(
                file=file_obj,
                bucket=NOTICES_BUCKET,
                allowed_extensions=NOTICES_ALLOWED_EXTENSIONS,
                max_size_bytes=NOTICES_MAX_SIZE_BYTES,
            )

        req = NoticeCreate(
            title=title,
            category=category,
            year=year,
            class_id=class_id,
            description=description,
            youtube_url=youtube_url,
            file_path=storage_path,
            public_url=public_url,
            file_type=file_type,
            is_visible=is_visible,
            is_pinned=is_pinned,
            expires_at=expires_at_raw,
        )

        try:
            return service.create_notice(req=req, current_user=current_user, ip_address=client_ip)
        except Exception:
            if storage_path:
                cleanup_storage_file(NOTICES_BUCKET, storage_path)
            raise

    raise BadRequestError("Unsupported Content-Type. Expected application/json or multipart/form-data.")


# ── PATCH /api/v1/notices/{notice_id} ─────────────────────────────────────────

@router.patch(
    "/{notice_id}",
    response_model=NoticeOut,
    summary="Update official notice (admin)",
    description="Admin only. Updates an official notice with centralized audit logging.",
)
async def update_notice(
    notice_id: int,
    req: NoticeUpdate,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NoticeOut:
    """Update an existing official notice."""
    client_ip = request.client.host if request.client else None
    service = NoticesService(db)
    return service.update_notice(
        notice_id=notice_id,
        req=req,
        current_user=current_user,
        ip_address=client_ip,
    )


# ── DELETE /api/v1/notices/{notice_id} ────────────────────────────────────────

@router.delete(
    "/{notice_id}",
    response_model=NoticeDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete official notice (admin)",
    description="Admin only. Deletes notice, queues storage file cleanup into outbox, and logs audit event atomically.",
)
async def delete_notice(
    notice_id: int,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NoticeDeleteResponse:
    """Delete an official notice."""
    client_ip = request.client.host if request.client else None
    service = NoticesService(db)
    return service.delete_notice(
        notice_id=notice_id,
        current_user=current_user,
        ip_address=client_ip,
    )