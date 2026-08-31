"""
Pydantic schemas for the User Profile & Account domain.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserStats(BaseModel):
    """User contribution statistics."""

    total_submissions: int = Field(default=0, description="Total submissions uploaded")
    published_count: int = Field(default=0, description="Total approved and published papers")
    pending_count: int = Field(default=0, description="Total submissions currently under review")
    rejected_count: int = Field(default=0, description="Total submissions rejected")


class UserProfileResponse(BaseModel):
    """Current authenticated user profile output."""

    id: str = Field(..., description="User database UUID")
    firebase_uid: str = Field(..., description="Verified Firebase UID")
    email: Optional[str] = Field(None, description="Account email (read-only from Google)")
    display_name: str = Field(..., description="Public contribution display name")
    photo_url: Optional[str] = Field(None, description="Google profile photo URL")
    role: str = Field(default="USER", description="Account role: USER, CONTRIBUTOR, ADMIN, SUPER_ADMIN")
    badge: str = Field(default="User", description="Calculated contribution badge")
    rank: Optional[int] = Field(None, description="Rank on the public leaderboard if active")
    stats: UserStats = Field(default_factory=UserStats, description="User contribution statistics")
    created_at: Optional[datetime] = Field(None, description="Account creation date")


class UpdateProfileRequest(BaseModel):
    """Request payload to update public contribution/display name."""

    display_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Desired public contribution name",
    )
