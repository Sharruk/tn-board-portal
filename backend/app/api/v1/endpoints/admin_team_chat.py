"""
Admin Team Chat Endpoints (Admin & Super Admin Only).
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.schemas.admin_team_chat import (
    AdminGroupMessageCreateRequest,
    AdminGroupMessageListResponse,
    AdminGroupMessageResponse,
)
from app.services.admin_team_chat_service import AdminTeamChatService

router = APIRouter(prefix="/admin/team-chat", tags=["Admin Team Chat"])


@router.get(
    "/messages",
    response_model=AdminGroupMessageListResponse,
    summary="Fetch Admin Team Chat messages in chronological order",
)
def get_team_chat_messages(
    limit: int = Query(50, ge=1, le=100, description="Max messages to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Retrieve shared admin group chat history ordered chronologically."""
    service = AdminTeamChatService(db)
    return service.get_messages(limit=limit, offset=offset)


@router.post(
    "/messages",
    response_model=AdminGroupMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post a message to Admin Team Chat",
)
def send_team_chat_message(
    req: AdminGroupMessageCreateRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Post an internal group message to the Admin Team Chat."""
    service = AdminTeamChatService(db)
    return service.send_message(current_user, req)

