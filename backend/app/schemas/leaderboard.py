"""
Pydantic schemas for the Contributor Leaderboard.
"""

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """A single contributor entry on the public leaderboard."""

    rank: int = Field(..., description="Rank on the leaderboard (1-indexed)")
    contributor_name: str = Field(..., description="Public display name or contributor pseudonym")
    total_contributions: int = Field(..., description="Total submissions submitted")
    accepted_contributions: int = Field(..., description="Total submissions approved/published")
    acceptance_rate: float = Field(..., description="Percentage of submissions accepted (0.0 - 100.0)")


class LeaderboardResponse(BaseModel):
    """Wrapper response for the leaderboard listing."""

    data: list[LeaderboardEntry] = Field(default_factory=list, description="Leaderboard ranked entries")
    total_contributors: int = Field(default=0, description="Total unique contributors")
