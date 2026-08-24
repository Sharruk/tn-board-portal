"""
Leaderboard service — aggregates contributor contributions and computes rankings.
"""

import logging
from collections import defaultdict
from typing import Any

from supabase import Client

from app.repositories.leaderboard_repository import LeaderboardRepository
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

logger = logging.getLogger(__name__)


class LeaderboardService:
    """Service layer for leaderboard business logic."""

    def __init__(self, db: Client) -> None:
        self._repo = LeaderboardRepository(db)

    def get_leaderboard(self, limit: int = 50) -> LeaderboardResponse:
        """
        Compute and return ranked leaderboard entries.

        Ranking rules:
          1. Accepted contributions (DESC)
          2. Acceptance rate (DESC)
          3. Total contributions (DESC)
          4. Contributor name (ASC)

        All emails and internal IDs are strictly stripped.
        """
        rows = self._repo.get_raw_submissions_for_leaderboard()

        if not rows:
            return LeaderboardResponse(data=[], total_contributors=0)

        # Aggregate by identity: key on firebase_uid if available, else publisher_name
        contributor_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "name": "Anonymous Contributor",
                "total": 0,
                "accepted": 0,
            }
        )

        for row in rows:
            name = (row.get("publisher_name") or "").strip() or "Anonymous Contributor"
            uid = row.get("firebase_uid")
            key = uid if uid else name.lower()

            stats = contributor_stats[key]
            # Keep the latest or best non-empty name
            if name and (stats["name"] == "Anonymous Contributor" or not stats["name"]):
                stats["name"] = name
            elif name and stats["name"] != name and not uid:
                stats["name"] = name

            stats["total"] += 1
            if row.get("status") == "approved":
                stats["accepted"] += 1

        # Compute acceptance rate and prepare list
        ranked_list: list[dict[str, Any]] = []
        for stats in contributor_stats.values():
            total = stats["total"]
            accepted = stats["accepted"]
            rate = round((accepted / total * 100.0), 1) if total > 0 else 0.0

            ranked_list.append(
                {
                    "contributor_name": stats["name"],
                    "total_contributions": total,
                    "accepted_contributions": accepted,
                    "acceptance_rate": rate,
                }
            )

        # Sort based on specified criteria
        ranked_list.sort(
            key=lambda x: (
                x["accepted_contributions"],
                x["acceptance_rate"],
                x["total_contributions"],
            ),
            reverse=True,
        )

        # Slice limit and assign 1-indexed ranks
        limited = ranked_list[:limit]
        entries: list[LeaderboardEntry] = []
        for idx, item in enumerate(limited, start=1):
            entries.append(
                LeaderboardEntry(
                    rank=idx,
                    contributor_name=item["contributor_name"],
                    total_contributions=item["total_contributions"],
                    accepted_contributions=item["accepted_contributions"],
                    acceptance_rate=item["acceptance_rate"],
                )
            )

        return LeaderboardResponse(
            data=entries,
            total_contributors=len(contributor_stats),
        )
