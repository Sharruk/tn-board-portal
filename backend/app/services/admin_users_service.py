"""
Admin Users service — business logic for Admin User Management.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.repositories.admin_users_repository import AdminUsersRepository
from app.services.leaderboard_service import LeaderboardService, compute_badges
from app.schemas.admin_users import (
    AdminUserConversationItem,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserSubmissionItem,
)
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class AdminUsersService:
    """Service layer for Admin User Management."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AdminUsersRepository(db)

    def get_users_list(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AdminUserListResponse:
        """Fetch paginated registered users with submission stats and leaderboard ranking."""
        rows, total = self._repo.get_users_list(search=search, limit=limit, offset=offset)
        summary = self._repo.get_summary_counts()

        # Build leaderboard rank lookup map
        lb = LeaderboardService(self._db).get_leaderboard(limit=100)
        rank_by_name: dict[str, tuple[int, float]] = {}
        for entry in lb.data:
            rank_by_name[entry.contributor_name.strip().lower()] = (
                entry.rank,
                entry.acceptance_rate,
            )

        items: list[AdminUserListItem] = []
        for r in rows:
            name = (r.get("display_name") or "").strip().lower()
            rank_info = rank_by_name.get(name) if name else None
            rank = rank_info[0] if rank_info else None
            rate = rank_info[1] if rank_info else None

            published_count = r.get("published_count", 0)
            badges = compute_badges(published_count, rank=rank or 0)

            items.append(
                AdminUserListItem(
                    id=r["id"],
                    firebase_uid=r["firebase_uid"],
                    email=r.get("email"),
                    display_name=r.get("display_name"),
                    photo_url=r.get("photo_url"),
                    role=r.get("role") or "USER",
                    is_active=r.get("is_active", True),
                    created_at=r.get("created_at"),
                    last_active_at=r.get("last_active_at"),
                    total_submissions=r.get("total_submissions", 0),
                    published_count=published_count,
                    pending_count=r.get("pending_count", 0),
                    rejected_count=r.get("rejected_count", 0),
                    leaderboard_rank=rank,
                    acceptance_rate=rate,
                    badges=badges,
                )
            )

        return AdminUserListResponse(
            data=items,
            total=total,
            total_registered_users=summary["total_users"],
            total_contributors=summary["total_contributors"],
        )

    def get_user_detail(self, firebase_uid: str) -> AdminUserDetailResponse:
        """Fetch full user details, all their submissions, and conversations."""
        user_row = self._repo.get_user_by_firebase_uid(firebase_uid)
        if not user_row:
            raise NotFoundError(resource="User", identifier=firebase_uid)

        # Leaderboard info
        name = (user_row.get("display_name") or "").strip().lower()
        rank = None
        rate = None
        if name:
            lb = LeaderboardService(self._db).get_leaderboard(limit=100)
            for entry in lb.data:
                if entry.contributor_name.strip().lower() == name:
                    rank = entry.rank
                    rate = entry.acceptance_rate
                    break

        published_count = user_row.get("published_count", 0)
        badges = compute_badges(published_count, rank=rank or 0)

        user_item = AdminUserListItem(
            id=user_row["id"],
            firebase_uid=user_row["firebase_uid"],
            email=user_row.get("email"),
            display_name=user_row.get("display_name"),
            photo_url=user_row.get("photo_url"),
            role=user_row.get("role") or "USER",
            is_active=user_row.get("is_active", True),
            created_at=user_row.get("created_at"),
            last_active_at=user_row.get("last_active_at"),
            total_submissions=user_row.get("total_submissions", 0),
            published_count=published_count,
            pending_count=user_row.get("pending_count", 0),
            rejected_count=user_row.get("rejected_count", 0),
            leaderboard_rank=rank,
            acceptance_rate=rate,
            badges=badges,
        )

        # User Submissions
        sub_rows = self._repo.get_user_submissions(firebase_uid, user_row.get("email"))
        submissions = [
            AdminUserSubmissionItem(
                id=s["id"],
                publisher_name=s["publisher_name"],
                details=s.get("details"),
                status=s["status"],
                rejection_reason=s.get("rejection_reason"),
                thank_you_message=s.get("thank_you_message"),
                created_at=s["created_at"],
                reviewed_at=s.get("reviewed_at"),
                file_count=s.get("file_count", 0),
                published_papers=s.get("published_papers", []),
            )
            for s in sub_rows
        ]

        # User Conversations
        conv_rows = self._repo.get_user_conversations(firebase_uid)
        conversations = [
            AdminUserConversationItem(
                id=c["id"],
                category=c["category"],
                subject=c["subject"],
                status=c["status"],
                unread_count=c.get("unread_count", 0),
                last_message=c.get("last_message"),
                updated_at=c["updated_at"],
                created_at=c["created_at"],
            )
            for c in conv_rows
        ]

        return AdminUserDetailResponse(
            user=user_item,
            submissions=submissions,
            conversations=conversations,
        )
