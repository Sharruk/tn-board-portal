"""
Official Notices service — business logic for notices, centralized audit logging,
and transactional outbox side-effects.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.repositories.admin_activity_repository import AdminActivityRepository
from app.repositories.notices_repository import NoticesRepository
from app.repositories.outbox_repository import OutboxRepository
from app.schemas.notice import (
    NoticeCreate,
    NoticeDeleteResponse,
    NoticeListResponse,
    NoticeOut,
    NoticeUpdate,
)
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class NoticesService:
    """Business logic for official notices."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._db = db
        self._repo = NoticesRepository(db)
        self._activity_repo = AdminActivityRepository(db)
        self._outbox_repo = OutboxRepository(db)

    def create_notice(
        self,
        req: NoticeCreate,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> NoticeOut:
        """Create a new official notice with atomic audit logging."""
        logger.info("NoticesService.create_notice: %s", req.title)
        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        try:
            notice = self._repo.create_notice(
                title=req.title,
                category=req.category,
                year=req.year,
                description=req.description,
                class_id=req.class_id,
                file_path=req.file_path,
                public_url=req.public_url,
                file_type=req.file_type,
                youtube_url=req.youtube_url,
                is_visible=req.is_visible,
                is_pinned=req.is_pinned,
                expires_at=req.expires_at,
                auto_commit=False,
            )
            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="NOTICE_CREATED",
                target_type="notice",
                target_id=str(notice["id"]),
                target_title=notice["title"],
                reason=None,
                metadata={
                    "notice_id": notice["id"],
                    "title": notice["title"],
                    "category": notice["category"],
                    "year": notice["year"],
                    "class_id": notice["class_id"],
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return NoticeOut(**notice)
        except Exception:
            self._db.rollback()
            raise

    def get_notice(self, notice_id: int) -> NoticeOut:
        """Retrieve a single official notice."""
        row = self._repo.get_by_id(notice_id)
        if not row:
            raise NotFoundError(resource="Notice", identifier=notice_id)
        return NoticeOut(**row)

    def list_notices(
        self,
        category: Optional[str] = None,
        class_id: Optional[int] = None,
        year: Optional[int] = None,
        is_visible: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> NoticeListResponse:
        """List official notices with pagination."""
        rows, total = self._repo.list_notices(
            category=category,
            class_id=class_id,
            year=year,
            is_visible=is_visible,
            limit=limit,
            offset=offset,
        )
        return NoticeListResponse(
            data=[NoticeOut(**r) for r in rows],
            total=total,
        )

    def update_notice(
        self,
        notice_id: int,
        req: NoticeUpdate,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> NoticeOut:
        """Update an official notice with atomic audit logging."""
        existing = self._repo.get_by_id(notice_id)
        if not existing:
            raise NotFoundError(resource="Notice", identifier=notice_id)

        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        updates = req.model_dump(exclude_unset=True)
        if not updates:
            return NoticeOut(**existing)

        try:
            updated = self._repo.update_notice(notice_id, updates, auto_commit=False)
            if not updated:
                raise NotFoundError(resource="Notice", identifier=notice_id)

            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="NOTICE_UPDATED",
                target_type="notice",
                target_id=str(notice_id),
                target_title=updated.get("title") or existing.get("title"),
                reason=None,
                metadata={
                    "notice_id": notice_id,
                    "changes": list(updates.keys()),
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return NoticeOut(**updated)
        except Exception:
            self._db.rollback()
            raise

    def delete_notice(
        self,
        notice_id: int,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> NoticeDeleteResponse:
        """
        Delete an official notice, queue storage deletion in outbox, and write audit log atomically.
        """
        existing = self._repo.get_by_id(notice_id)
        if not existing:
            raise NotFoundError(resource="Notice", identifier=notice_id)

        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        file_path = existing.get("file_path")
        if not file_path and existing.get("public_url"):
            pub_url = existing["public_url"]
            if "/official-updates/" in pub_url:
                file_path = pub_url.split("/official-updates/")[-1].split("?")[0]

        try:
            self._repo.delete_notice(notice_id, auto_commit=False)

            if file_path:
                self._outbox_repo.enqueue(
                    bucket_name="official-updates",
                    object_path=file_path,
                    operation="DELETE",
                    payload={"notice_id": notice_id, "title": existing.get("title")},
                    idempotency_key=f"notice-delete-{notice_id}-{file_path}",
                )

            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="NOTICE_DELETED",
                target_type="notice",
                target_id=str(notice_id),
                target_title=existing.get("title") or f"Notice {notice_id}",
                reason=None,
                metadata={
                    "notice_id": notice_id,
                    "title": existing.get("title"),
                    "file_path": file_path,
                    "storage_queued": bool(file_path),
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return NoticeDeleteResponse(
                id=notice_id,
                deleted=True,
                storage_deleted=True,
                message="Notice deleted successfully",
            )
        except Exception:
            self._db.rollback()
            raise