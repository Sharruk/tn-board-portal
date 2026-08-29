"""
Pydantic schemas for the Community discussion platform, requests, and profiles.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Create / Update schemas ───────────────────────────────────────────────────

class PostCreate(BaseModel):
    """Payload for creating a new community discussion post."""

    title: str = Field(..., min_length=3, max_length=200, description="Discussion title")
    content: str = Field(..., min_length=3, max_length=5000, description="Discussion body text")
    category: str = Field("Discussion", description="Category: Discussion, Question, Paper Request, Suggestion, Problem Report")
    author_avatar: Optional[str] = Field(None, description="Author avatar URL")


class PostUpdate(BaseModel):
    """Payload for editing an existing post."""

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=3, max_length=5000)
    category: Optional[str] = None
    status: Optional[str] = None  # 'open', 'resolved', 'closed'


class CommentCreate(BaseModel):
    """Payload for replying/commenting on a community post."""

    content: str = Field(..., min_length=1, max_length=2000, description="Comment text")
    parent_id: Optional[str] = Field(None, description="Parent comment ID for nested replies")
    author_avatar: Optional[str] = Field(None, description="Author avatar URL")


class ReportCreate(BaseModel):
    """Payload for reporting inappropriate content."""

    target_type: str = Field(..., description="'post', 'comment', 'paper_comment', 'request'")
    target_id: str = Field(..., description="Target entity ID")
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for report")


class PaperRequestCreate(BaseModel):
    """Payload for submitting a paper request."""

    title: str = Field(..., min_length=3, max_length=255)
    class_id: Optional[int] = None
    subject_id: Optional[int] = None
    exam_type: str = Field(..., min_length=2, max_length=100)
    year: int = Field(..., ge=2000, le=2050)
    month: Optional[str] = None
    district: Optional[str] = None
    description: Optional[str] = None
    author_avatar: Optional[str] = None


# ── Output schemas ────────────────────────────────────────────────────────────

class CommentOut(BaseModel):
    """Single comment output schema."""

    id: str
    post_id: str
    author_name: str
    author_avatar: Optional[str] = None
    firebase_uid: Optional[str] = None
    parent_id: Optional[str] = None
    content: str
    created_at: datetime
    replies: list["CommentOut"] = Field(default_factory=list)


class PostListItem(BaseModel):
    """Post item for community feed listing."""

    id: str
    title: str
    content: str
    category: str = "Discussion"
    status: str = "open"
    author_name: str
    author_avatar: Optional[str] = None
    firebase_uid: Optional[str] = None
    upvotes: int = 0
    likes_count: int = 0
    reply_count: int = 0
    comments_count: int = 0
    is_pinned: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class PostOut(BaseModel):
    """Detailed post output schema with nested comments."""

    id: str
    title: str
    content: str
    category: str = "Discussion"
    status: str = "open"
    author_name: str
    author_avatar: Optional[str] = None
    firebase_uid: Optional[str] = None
    upvotes: int = 0
    likes_count: int = 0
    reply_count: int = 0
    comments_count: int = 0
    is_pinned: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    comments: list[CommentOut] = Field(default_factory=list)


class PostListResponse(BaseModel):
    """Paginated response for community posts."""

    data: list[PostListItem]
    total: int
    page: int
    page_size: int
    has_next: bool


class PaperRequestOut(BaseModel):
    """Paper request output schema."""

    id: str
    author_name: str
    author_avatar: Optional[str] = None
    firebase_uid: Optional[str] = None
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    exam_type: str
    year: int
    month: Optional[str] = None
    district: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str = "open"
    fulfilled_paper_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class PaperRequestListResponse(BaseModel):
    """Paginated paper requests."""

    data: list[PaperRequestOut]
    total: int
    page: int
    page_size: int


class UserProfileOut(BaseModel):
    """Public user profile."""

    display_name: str
    avatar_url: Optional[str] = None
    joined_date: datetime
    approved_contributions: int = 0
    likes_received: int = 0
    posts_count: int = 0
    comments_count: int = 0
    badges: list[str] = Field(default_factory=list)
