"""
Admin Team Chat service — business logic for Admin Group Messaging.
"""

import logging
from typing import Any
from sqlalchemy.orm import Session

from app.repositories.admin_team_chat_repository import AdminTeamChatRepository
from app.schemas.admin_team_chat import (
    AdminGroupMessageCreateRequest,
    AdminGroupMessageListResponse,
    AdminGroupMessageResponse,
)
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


def derive_admin_display_name(display_name: str | None, email: str | None) -> str:
    """Clean admin display name: if all caps title case it, fallback to email prefix."""
    raw = (display_name or "").strip()
    if not raw and email:
        raw = email.split("@")[0].strip()
    if raw:
        return raw.title() if raw.isupper() and len(raw) > 3 else raw
    return "Admin"


class AdminTeamChatService:
    """Business logic for admin group chat."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AdminTeamChatRepository(db)

    def get_messages(self, limit: int = 50, offset: int = 0) -> AdminGroupMessageListResponse:
        """Fetch chronological team chat messages."""
        items, total = self._repo.get_messages(limit=limit, offset=offset)
        data = [AdminGroupMessageResponse(**m) for m in items]
        return AdminGroupMessageListResponse(
            data=data,
            total=total,
            limit=limit,
            offset=offset,
        )

    def send_message(
        self, current_user: dict[str, Any], req: AdminGroupMessageCreateRequest
    ) -> AdminGroupMessageResponse:
        """
        Send a group message.
        CRITICAL: sender identity (uid, email, name, role) is derived entirely
        from the authenticated current_user context, never from client input.
        """
        message = req.message.strip()
        if not message:
            raise ValidationError("Message cannot be empty.")
        if len(message) > 5000:
            raise ValidationError("Message exceeds maximum length of 5000 characters.")

        uid = current_user.get("firebase_uid") or current_user.get("id") or ""
        email = current_user.get("email") or ""
        raw_role = current_user.get("role") or "ADMIN"
        role = "SUPER_ADMIN" if raw_role.upper() == "SUPER_ADMIN" else "ADMIN"
        name = derive_admin_display_name(current_user.get("display_name"), email)

        msg_dict = self._repo.add_message(
            sender_firebase_uid=uid,
            sender_email=email,
            sender_name=name,
            sender_role=role,
            message=message,
        )
        return AdminGroupMessageResponse(**msg_dict)

