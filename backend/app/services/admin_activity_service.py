"""
Admin Activity service — business logic for immutable platform audit logs.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.repositories.admin_activity_repository import AdminActivityRepository
from app.schemas.admin_activity import AdminActivityItem, AdminActivityListResponse

logger = logging.getLogger(__name__)


class AdminActivityService:
    """Service layer for recording and viewing admin activity."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AdminActivityRepository(db)

    def log_activity(
        self,
        actor: dict[str, Any],
        action: str,
        target_type: str,
        target_id: str,
        target_title: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        auto_commit: bool = True,
    ) -> dict[str, Any]:
        """Record an administrative action performed by an actor."""
        actor_uid = actor.get("firebase_uid") or actor.get("uid") or "system"
        actor_email = actor.get("email") or "system@hungrylearner.internal"
        actor_name = actor.get("display_name") or actor.get("name") or actor_email.split("@")[0]
        actor_role = actor.get("role") or ("SUPER_ADMIN" if actor.get("is_super_admin") else "ADMIN")

        return self._repo.log_activity(
            actor_uid=actor_uid,
            actor_email=actor_email,
            actor_name=actor_name,
            actor_role=actor_role,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            target_title=target_title,
            reason=reason,
            metadata=metadata,
            ip_address=ip_address,
            auto_commit=auto_commit,
        )

    def list_activities(
        self,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> AdminActivityListResponse:
        """Fetch paginated activity history."""
        limit = min(100, max(1, limit))
        offset = max(0, offset)
        items, total = self._repo.list_activities(
            limit=limit,
            offset=offset,
            action=action,
            target_type=target_type,
        )
        return AdminActivityListResponse(
            data=[AdminActivityItem(**it) for it in items],
            total=total,
            limit=limit,
            offset=offset,
        )
