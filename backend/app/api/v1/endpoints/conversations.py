"""
Student Conversations & Messaging Endpoints.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.supabase import get_db
from app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.conversations_service import ConversationsService

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new support conversation",
)
def create_conversation(
    req: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new categorized inquiry/support conversation with TN Board Admin."""
    service = ConversationsService(db)
    return service.create_conversation(current_user, req)


@router.get(
    "/me",
    response_model=ConversationListResponse,
    summary="List current user's conversations",
)
def get_my_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all support conversations opened by the authenticated student."""
    service = ConversationsService(db)
    return service.get_user_conversations(current_user, limit=limit, offset=offset)


@router.get(
    "/unread-count",
    summary="Get unread message count for authenticated user",
)
def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the number of unread admin messages across user's conversations."""
    service = ConversationsService(db)
    return service.get_user_unread_count(current_user)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation detail and message thread",
)
def get_conversation_detail(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch complete conversation thread and mark admin messages as read."""
    service = ConversationsService(db)
    return service.get_user_conversation_detail(current_user, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a reply in an existing conversation",
)
def add_message(
    conversation_id: str,
    req: MessageCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Post a message to an existing conversation thread."""
    service = ConversationsService(db)
    return service.add_user_message(current_user, conversation_id, req)
