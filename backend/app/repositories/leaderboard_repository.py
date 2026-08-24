"""
Leaderboard repository — data access for contributor rankings.
"""

import logging
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)


class LeaderboardRepository:
    """Data access layer for leaderboard calculations from submissions."""

    def __init__(self, db: Client) -> None:
        self._db = db

    def get_raw_submissions_for_leaderboard(self) -> list[dict[str, Any]]:
        """
        Fetch submission records needed to compute contributor leaderboard.
        Only reads public identity fields and status (no sensitive info).
        """
        response = (
            self._db.table("submissions")
            .select("publisher_name,firebase_uid,status,created_at")
            .execute()
        )
        return response.data or []
