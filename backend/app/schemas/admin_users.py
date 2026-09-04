"""
Pydantic schemas for Admin User Management.
"""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel


class AdminUserListItem(BaseModel):
    """User summary item for Admin Users list."""
    id: str
    firebase_uid: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None
    total_submissions: int = 0
    published_count: int = 0
    pending_count: int = 0
    rejected_count: int = 0
    leaderboard_rank: Optional[int] = None
    acceptance_rate: Optional[float] = None
    badges: List[str] = []


class AdminUserListResponse(BaseModel):
    """Response containing paginated list of registered users for admin."""
    data: List[AdminUserListItem]
    total: int
    total_registered_users: int
    total_contributors: int


class AdminUserSubmissionItem(BaseModel):
    """Submission item included in User Detail view for admin."""
    id: str
    publisher_name: str
    details: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    thank_you_message: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    file_count: int = 0
    published_papers: List[dict[str, Any]] = []


class AdminUserConversationItem(BaseModel):
    """Conversation summary included in User Detail view for admin."""
    id: str
    category: str
    subject: str
    status: str
    unread_count: int = 0
    last_message: Optional[str] = None
    updated_at: datetime
    created_at: datetime


class AdminUserDetailResponse(BaseModel):
    """In-depth user detail view for admin."""
    user: AdminUserListItem
    submissions: List[AdminUserSubmissionItem] = []
    conversations: List[AdminUserConversationItem] = []
