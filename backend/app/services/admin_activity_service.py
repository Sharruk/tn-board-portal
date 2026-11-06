"""
Admin Activity service — business logic for Central Admin Activity Logs.
"""

from datetime import datetime
import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.repositories.admin_activity_repository import AdminActivityRepository
from app.schemas.admin_activity import (
    AdminActivityLogListResponse,
    AdminActivityLogResponse,
)
from app.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


class AdminActivityService:
    """Service layer for querying admin activity logs."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AdminActivityRepository(db)

    def get_activity_logs(
        self,
        *,
        actor_uid: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AdminActivityLogListResponse:
        """
        Retrieve paginated activity logs with validation and filtering.
        """
        # Validate date logic
        if start_date and end_date and start_date > end_date:
            raise ValidationError("start_date cannot be later than end_date.")

        items, total = self._repo.get_activity_logs(
            actor_uid=actor_uid,
            action=action,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        data = [AdminActivityLogResponse(**item) for item in items]

        return AdminActivityLogListResponse(
            data=data,
            total=total,
            limit=limit,
            offset=offset,
        )