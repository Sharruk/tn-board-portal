"""
Pydantic schemas for Student-to-Admin Messaging and Support Conversations.
"""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class MessageCreateRequest(BaseModel):
    """Payload to send a message / reply in a conversation."""
    message: str = Field(..., min_length=1, max_length=5000, description="Message text content")


class MessageResponse(BaseModel):
    """A single message inside a conversation."""
    id: str
    conversation_id: str
    sender_role: str = Field(..., description="'user' or 'admin'")
    sender_firebase_uid: str
    sender_name: str
    message: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class ConversationCreateRequest(BaseModel):
    """Payload to start a new support conversation."""
    category: str = Field(
        ...,
        description="Category: 'general_question', 'material_request', 'submission_status', 'report_problem', 'feedback', 'other'"
    )
    subject: str = Field(..., min_length=3, max_length=255, description="Subject or inquiry summary")
    message: str = Field(..., min_length=1, max_length=5000, description="Initial message")
    submission_id: Optional[str] = Field(None, description="Optional UUID of related paper submission")


class LinkedSubmissionInfo(BaseModel):
    """Contextual submission information attached to a conversation."""
    id: str
    publisher_name: str
    details: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    thank_you_message: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    files_count: int = 0
    published_papers: List[dict[str, Any]] = []


class StudentContext(BaseModel):
    """Context about the student for admin resolution."""
    firebase_uid: str
    display_name: str
    email: Optional[str] = None
    photo_url: Optional[str] = None
    total_submissions: int = 0
    published_count: int = 0
    pending_count: int = 0
    rejected_count: int = 0
    leaderboard_rank: Optional[int] = None
    acceptance_rate: Optional[float] = None
    created_at: Optional[datetime] = None
    last_active_at: Optional[datetime] = None


class ConversationListItem(BaseModel):
    """Summary item for conversation lists."""
    id: str
    firebase_uid: str
    user_email: str
    user_display_name: str
    user_photo_url: Optional[str] = None
    category: str
    subject: str
    status: str
    submission_id: Optional[str] = None
    unread_count: int = 0
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_message_sender_role: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """List of conversations."""
    data: List[ConversationListItem]
    total: int


class ConversationDetailResponse(BaseModel):
    """Detailed conversation view with full message thread and contextual data."""
    id: str
    firebase_uid: str
    user_email: str
    user_display_name: str
    user_photo_url: Optional[str] = None
    category: str
    subject: str
    status: str
    submission_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]
    linked_submission: Optional[LinkedSubmissionInfo] = None
    student_context: Optional[StudentContext] = None


class ConversationStatusUpdateRequest(BaseModel):
    """Payload to update conversation status."""
    status: str = Field(..., description="'open', 'awaiting_admin', 'awaiting_user', 'resolved'")


class AdminConversationStatsResponse(BaseModel):
    """Admin summary statistics for conversation inbox."""
    total: int = 0
    unread_count: int = 0
    awaiting_admin: int = 0
    awaiting_user: int = 0
    resolved: int = 0
