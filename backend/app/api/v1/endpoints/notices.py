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
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
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
    description="Admin only. Creates an official notice with centralized audit logging.",
)
async def create_notice(
    req: NoticeCreate,
    request: Request,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NoticeOut:
    """Create a new official notice."""
    client_ip = request.client.host if request.client else None
    service = NoticesService(db)
    return service.create_notice(req=req, current_user=current_user, ip_address=client_ip)


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