"""
News & Updates service — business logic for articles, centralized audit logging,
and transactional outbox side-effects.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.repositories.admin_activity_repository import AdminActivityRepository
from app.repositories.news_repository import NewsRepository
from app.repositories.outbox_repository import OutboxRepository
from app.schemas.news import (
    NewsCreate,
    NewsDeleteResponse,
    NewsListResponse,
    NewsOut,
    NewsUpdate,
)
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


def _extract_storage_path(url: Optional[str], bucket: str = "news-media") -> Optional[str]:
    """Extract storage relative object path from a public CDN URL."""
    if not url:
        return None
    marker = f"/{bucket}/"
    if marker in url:
        return url.split(marker)[-1].split("?")[0]
    return None


class NewsService:
    """Business logic for news & updates."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._db = db
        self._repo = NewsRepository(db)
        self._activity_repo = AdminActivityRepository(db)
        self._outbox_repo = OutboxRepository(db)

    def create_news(
        self,
        req: NewsCreate,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> NewsOut:
        """Create a new news article with atomic audit logging."""
        logger.info("NewsService.create_news: %s", req.title)
        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        try:
            article = self._repo.create_news(
                title=req.title,
                category=req.category,
                summary=req.summary,
                content=req.content,
                tags=req.tags,
                thumbnail_url=req.thumbnail_url,
                thumbnail_alt=req.thumbnail_alt,
                youtube_url=req.youtube_url,
                pdf_url=req.pdf_url,
                class_id=req.class_id,
                district=req.district,
                status=req.status,
                is_pinned=req.is_pinned,
                published_at=req.published_at,
                auto_commit=False,
            )
            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="NEWS_CREATED",
                target_type="news",
                target_id=article["id"],
                target_title=article["title"],
                reason=None,
                metadata={
                    "news_id": article["id"],
                    "title": article["title"],
                    "category": article["category"],
                    "status": article["status"],
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return NewsOut(**article)
        except Exception:
            self._db.rollback()
            raise

    def get_news(self, news_id: str, allow_non_published: bool = False) -> NewsOut:
        """Retrieve a single news article. Public callers only receive published articles."""
        row = self._repo.get_by_id(news_id)
        if not row:
            raise NotFoundError(resource="News", identifier=news_id)
        if not allow_non_published and row.get("status") != "published":
            raise NotFoundError(resource="News", identifier=news_id)
        return NewsOut(**row)

    def list_news(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        class_id: Optional[int] = None,
        is_pinned: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
        published_only: bool = False,
    ) -> NewsListResponse:
        """List news articles with pagination."""
        rows, total = self._repo.list_news(
            status=status,
            category=category,
            class_id=class_id,
            is_pinned=is_pinned,
            limit=limit,
            offset=offset,
            published_only=published_only,
        )
        return NewsListResponse(
            data=[NewsOut(**r) for r in rows],
            total=total,
        )

    def update_news(
        self,
        news_id: str,
        req: NewsUpdate,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> NewsOut:
        """Update a news article with atomic audit logging."""
        existing = self._repo.get_by_id(news_id)
        if not existing:
            raise NotFoundError(resource="News", identifier=news_id)

        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        updates = req.model_dump(exclude_unset=True)
        if not updates:
            return NewsOut(**existing)

        try:
            updated = self._repo.update_news(news_id, updates, auto_commit=False)
            if not updated:
                raise NotFoundError(resource="News", identifier=news_id)

            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="NEWS_UPDATED",
                target_type="news",
                target_id=str(news_id),
                target_title=updated.get("title") or existing.get("title"),
                reason=None,
                metadata={
                    "news_id": str(news_id),
                    "changes": list(updates.keys()),
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return NewsOut(**updated)
        except Exception:
            self._db.rollback()
            raise

    def delete_news(
        self,
        news_id: str,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> NewsDeleteResponse:
        """
        Delete a news article, queue media storage cleanup in outbox, and log audit event atomically.
        """
        existing = self._repo.get_by_id(news_id)
        if not existing:
            raise NotFoundError(resource="News", identifier=news_id)

        actor_id = current_user.get("user_id") or current_user.get("firebase_uid") or current_user.get("id") or "system"
        actor_email = current_user.get("email") or "system@hungrylearner.internal"
        actor_name = current_user.get("display_name") or current_user.get("name") or actor_email
        actor_role = current_user.get("role") or "ADMIN"

        thumb_path = _extract_storage_path(existing.get("thumbnail_url"), "news-media")
        pdf_path = _extract_storage_path(existing.get("pdf_url"), "news-media")

        try:
            self._repo.delete_news(news_id, auto_commit=False)

            if thumb_path:
                self._outbox_repo.enqueue(
                    bucket_name="news-media",
                    object_path=thumb_path,
                    operation="DELETE",
                    payload={"news_id": news_id, "type": "thumbnail"},
                    idempotency_key=f"news-delete-{news_id}-thumb-{thumb_path}",
                )
            if pdf_path:
                self._outbox_repo.enqueue(
                    bucket_name="news-media",
                    object_path=pdf_path,
                    operation="DELETE",
                    payload={"news_id": news_id, "type": "pdf"},
                    idempotency_key=f"news-delete-{news_id}-pdf-{pdf_path}",
                )

            self._activity_repo.log_activity(
                actor_uid=actor_id,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="NEWS_DELETED",
                target_type="news",
                target_id=str(news_id),
                target_title=existing.get("title") or f"News {news_id}",
                reason=None,
                metadata={
                    "news_id": str(news_id),
                    "title": existing.get("title"),
                    "thumb_path": thumb_path,
                    "pdf_path": pdf_path,
                },
                ip_address=ip_address,
            )
            self._db.commit()
            return NewsDeleteResponse(
                id=news_id,
                deleted=True,
                storage_deleted=True,
                message="News article deleted successfully",
            )
        except Exception:
            self._db.rollback()
            raise