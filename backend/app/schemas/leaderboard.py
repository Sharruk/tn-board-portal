"""
Pydantic schemas for the Contributor Leaderboard.
"""

from typing import Optional
from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """A single contributor entry on the public leaderboard."""

    rank: int = Field(..., description="Rank on the leaderboard (1-indexed)")
    contributor_name: str = Field(..., description="Public display name or contributor pseudonym")
    avatar_url: Optional[str] = Field(None, description="Public avatar URL if available")
    submitted_count: int = Field(0, description="Total submissions submitted")
    approved_count: int = Field(0, description="Total approved/published contributions")
    rejected_count: int = Field(0, description="Total rejected submissions")
    pending_count: int = Field(0, description="Total pending submissions")
    total_contributions: int = Field(0, description="Legacy alias for total submitted files")
    accepted_contributions: int = Field(0, description="Total approved files")
    acceptance_rate: float = Field(0.0, description="Percentage of finalized submissions accepted (0.0 - 100.0)")
    badges: list[str] = Field(default_factory=list, description="Milestone and contribution badges")
    recent_contributions: list[str] = Field(default_factory=list, description="Titles/classes of recently approved papers")


class LeaderboardResponse(BaseModel):
    """Wrapper response for the leaderboard listing."""

    data: list[LeaderboardEntry] = Field(default_factory=list, description="Leaderboard ranked entries")
    total_contributors: int = Field(default=0, description="Total unique contributors")
