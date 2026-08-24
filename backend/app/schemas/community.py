"""
Pydantic schemas for the Community discussion platform.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ── Create schemas ────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    """Payload for creating a new community discussion post."""

    title: str = Field(..., min_length=3, max_length=200, description="Discussion title")
    content: str = Field(..., min_length=3, max_length=5000, description="Discussion body text")


class CommentCreate(BaseModel):
    """Payload for replying/commenting on a community post."""

    content: str = Field(..., min_length=1, max_length=2000, description="Comment text")


# ── Output schemas ────────────────────────────────────────────────────────────

class CommentOut(BaseModel):
    """Single comment output schema."""

    id: str
    post_id: str
    author_name: str
    content: str
    created_at: datetime


class PostListItem(BaseModel):
    """Post item for community feed listing."""

    id: str
    title: str
    content: str
    author_name: str
    upvotes: int = 0
    reply_count: int = 0
    is_pinned: bool = False
    created_at: datetime


class PostOut(BaseModel):
    """Detailed post output schema with nested comments."""

    id: str
    title: str
    content: str
    author_name: str
    upvotes: int = 0
    reply_count: int = 0
    is_pinned: bool = False
    created_at: datetime
    comments: list[CommentOut] = Field(default_factory=list)


class PostListResponse(BaseModel):
    """Paginated response for community posts."""

    data: list[PostListItem]
    total: int
    page: int
    page_size: int
    has_next: bool
