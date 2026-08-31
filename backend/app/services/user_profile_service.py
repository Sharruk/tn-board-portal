"""
User Profile service — business logic for user profiles, badges, and contribution names.
"""

import logging
import re
from sqlalchemy.orm import Session

from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.submissions_repository import SubmissionsRepository
from app.schemas.user_profile import UpdateProfileRequest, UserProfileResponse, UserStats
from app.utils.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

_SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9\s._\-',()]+$")


def calculate_badge(published_count: int, rank: int | None = None) -> str:
    """Compute contributor badge based on verified published contributions and leaderboard status."""
    if (rank is not None and rank <= 3) or published_count >= 15:
        return "🏆 Top Contributor"
    if published_count >= 5:
        return "⭐ Active Contributor"
    if published_count >= 1:
        return "🏅 Contributor"
    return "👤 User"


class UserProfileService:
    """Service layer for user profiles and account settings."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = UserProfileRepository(db)
        self._submissions_repo = SubmissionsRepository(db)

    def get_profile(self, current_user: dict) -> UserProfileResponse:
        """
        Build and return complete profile for current user including stats and calculated badge.
        """
        firebase_uid = current_user["firebase_uid"]
        email = current_user.get("email")

        user_row = self._repo.get_by_firebase_uid(firebase_uid)
        if not user_row:
            user_row = current_user

        stats_dict = self._submissions_repo.get_user_submission_stats(firebase_uid, email=email)
        stats = UserStats(
            total_submissions=stats_dict.get("total_submissions", 0),
            published_count=stats_dict.get("published_count", 0),
            pending_count=stats_dict.get("pending_count", 0),
            rejected_count=stats_dict.get("rejected_count", 0),
        )

        # Get leaderboard rank if user has published contributions
        rank = None
        if stats.published_count > 0:
            from app.services.leaderboard_service import LeaderboardService
            lb = LeaderboardService(self._db).get_leaderboard(limit=100)
            # Find matching rank
            user_name = (user_row.get("display_name") or "").strip().lower()
            for entry in lb.data:
                if entry.contributor_name.strip().lower() == user_name:
                    rank = entry.rank
                    break

        badge = calculate_badge(stats.published_count, rank=rank)
        display_name = user_row.get("display_name") or current_user.get("display_name") or "Contributor"

        return UserProfileResponse(
            id=str(user_row.get("id") or ""),
            firebase_uid=firebase_uid,
            email=email,
            display_name=display_name,
            photo_url=current_user.get("photo_url"),
            role=user_row.get("role", "USER"),
            badge=badge,
            rank=rank,
            stats=stats,
            created_at=user_row.get("created_at"),
        )

    def update_display_name(self, current_user: dict, req: UpdateProfileRequest) -> UserProfileResponse:
        """
        Update the public contribution name for the user.
        """
        new_name = req.display_name.strip()
        if len(new_name) < 2:
            raise ValidationError("Contribution name must be at least 2 characters.")
        if len(new_name) > 50:
            raise ValidationError("Contribution name must not exceed 50 characters.")
        if not _SAFE_NAME_RE.match(new_name):
            raise ValidationError("Contribution name contains invalid characters.")

        firebase_uid = current_user["firebase_uid"]
        self._repo.update_display_name(firebase_uid, new_name)

        # Re-fetch profile
        return self.get_profile(current_user)
