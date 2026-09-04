"""
Admin Conversations & Inbox Endpoints (Admin-Only).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.schemas.conversation import (
    AdminConversationStatsResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationStatusUpdateRequest,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.conversations_service import ConversationsService

router = APIRouter(prefix="/admin/conversations", tags=["Admin Conversations"])


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List all support conversations for Admin Inbox",
)
def get_admin_conversations(
    status: Optional[str] = Query(None, description="Filter by status or 'unread'"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search subject, user email, or name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all student inquiries and conversations with filters for Admin Inbox."""
    service = ConversationsService(db)
    return service.get_admin_conversations(
        status=status, category=category, search=search, limit=limit, offset=offset
    )


@router.get(
    "/stats",
    response_model=AdminConversationStatsResponse,
    summary="Get conversation counts and statistics",
)
def get_admin_conversation_stats(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Aggregate total, unread, and lifecycle counts for admin dashboard tabs."""
    service = ConversationsService(db)
    return service.get_admin_stats()


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation thread with full student context",
)
def get_admin_conversation_detail(
    conversation_id: str,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Open a conversation, mark user messages as read, and retrieve student contribution context."""
    service = ConversationsService(db)
    return service.get_admin_conversation_detail(conversation_id)


@router.post(
    "/{conversation_id}/reply",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin reply to a student conversation",
)
def admin_reply(
    conversation_id: str,
    req: MessageCreateRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Post an official admin reply and update status to 'awaiting_user'."""
    service = ConversationsService(db)
    return service.admin_reply(current_user, conversation_id, req)


@router.patch(
    "/{conversation_id}/status",
    response_model=ConversationDetailResponse,
    summary="Update conversation status (e.g. resolve or reopen)",
)
def update_conversation_status(
    conversation_id: str,
    req: ConversationStatusUpdateRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Change the lifecycle status of a conversation."""
    service = ConversationsService(db)
    return service.update_conversation_status(conversation_id, req.status)
