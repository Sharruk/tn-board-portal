"""
Leaderboard service — aggregates contributor contributions and computes rankings.
"""

import logging
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.leaderboard_repository import LeaderboardRepository
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

logger = logging.getLogger(__name__)


def compute_badges(approved_count: int, rank: int = 0) -> list[str]:
    """Compute contributor recognition badges based on approved contributions and rank."""
    badges: list[str] = []
    if approved_count >= 15 or (rank > 0 and rank <= 3):
        badges.append("Top Contributor")
    elif approved_count >= 5:
        badges.append("Active Contributor")
    elif approved_count >= 1:
        badges.append("Contributor")
    else:
        badges.append("User")
    return badges



class LeaderboardService:
    """Service layer for leaderboard business logic."""

    def __init__(self, db: Session) -> None:
        self._repo = LeaderboardRepository(db)

    def get_leaderboard(self, limit: int = 50) -> LeaderboardResponse:
        """
        Compute and return ranked leaderboard entries.

        Ranking rules:
          1. Approved contributions (DESC)
          2. Acceptance rate (DESC)
          3. Total submitted count (DESC)
          4. Contributor name (ASC)

        Acceptance rate is strictly:
          approved / (approved + rejected) * 100
        (Pending submissions are excluded from the rate denominator).

        All emails and internal IDs are strictly stripped.
        """
        rows = self._repo.get_raw_submissions_for_leaderboard()
        recent_papers_map = self._repo.get_recent_approved_papers_for_contributors()

        if not rows:
            return LeaderboardResponse(data=[], total_contributors=0)

        # Aggregate by identity: key on firebase_uid if available, else publisher_name
        contributor_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "name": "Anonymous Contributor",
                "submitted": 0,
                "approved": 0,
                "rejected": 0,
                "pending": 0,
                "key": "",
            }
        )

        for row in rows:
            name = (row.get("publisher_name") or "").strip() or "Anonymous Contributor"
            uid = row.get("firebase_uid")
            key = uid if uid else name.lower()

            stats = contributor_stats[key]
            stats["key"] = key
            # Keep the latest or best non-empty name
            if name and (stats["name"] == "Anonymous Contributor" or not stats["name"]):
                stats["name"] = name
            elif name and stats["name"] != name and not uid:
                stats["name"] = name

            file_cnt = int(row.get("file_count") or 1)
            stats["submitted"] += file_cnt

            st = str(row.get("status") or "").lower()
            if st == "approved":
                stats["approved"] += file_cnt
            elif st == "rejected":
                stats["rejected"] += file_cnt
            elif st == "pending":
                stats["pending"] += file_cnt

        # Filter out users with 0 submissions
        active_contributors = [
            stats for stats in contributor_stats.values()
            if stats["submitted"] > 0
        ]

        # Compute acceptance rate and prepare list
        ranked_list: list[dict[str, Any]] = []
        for stats in active_contributors:
            submitted = stats["submitted"]
            approved = stats["approved"]
            rejected = stats["rejected"]
            pending = stats["pending"]

            # Acceptance rate formula: approved / (approved + rejected) * 100
            decided = approved + rejected
            rate = round((approved / decided * 100.0), 1) if decided > 0 else (100.0 if approved > 0 else 0.0)

            badges = compute_badges(approved, rate)
            recent = recent_papers_map.get(stats["key"], [])[:3]

            ranked_list.append(
                {
                    "contributor_name": stats["name"],
                    "submitted_count": submitted,
                    "approved_count": approved,
                    "rejected_count": rejected,
                    "pending_count": pending,
                    "total_contributions": submitted,
                    "accepted_contributions": approved,
                    "acceptance_rate": rate,
                    "badges": badges,
                    "recent_contributions": recent,
                }
            )

        # Sort based on positive contribution criteria: Approved count first, then total submitted
        ranked_list.sort(
            key=lambda x: (
                x["approved_count"],
                x["submitted_count"],
                x["acceptance_rate"],
            ),
            reverse=True,
        )

        # Slice limit and assign 1-indexed ranks and badges
        limited = ranked_list[:limit]
        entries: list[LeaderboardEntry] = []
        for idx, item in enumerate(limited, start=1):
            badges = compute_badges(item["approved_count"], rank=idx)
            entries.append(
                LeaderboardEntry(
                    rank=idx,
                    contributor_name=item["contributor_name"],
                    submitted_count=item["submitted_count"],
                    approved_count=item["approved_count"],
                    rejected_count=item["rejected_count"],
                    pending_count=item["pending_count"],
                    total_contributions=item["total_contributions"],
                    accepted_contributions=item["accepted_contributions"],
                    acceptance_rate=item["acceptance_rate"],
                    badges=badges,
                    recent_contributions=item["recent_contributions"],
                )
            )


        return LeaderboardResponse(
            data=entries,
            total_contributors=len(active_contributors),
        )
