"""
Pydantic schemas for News & Updates.
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

NewsStatus = Literal["draft", "published", "archived"]


class NewsBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=400, description="Article title")
    summary: Optional[str] = Field(None, description="Short summary snippet")
    content: Optional[str] = Field(None, description="Full article content (markdown/html)")
    category: str = Field(..., description="News category")
    tags: List[str] = Field(default_factory=list, description="Tags")
    thumbnail_url: Optional[str] = Field(None, description="Image thumbnail CDN URL")
    thumbnail_alt: Optional[str] = Field(None, description="Alt text for thumbnail")
    youtube_url: Optional[str] = Field(None, description="Optional YouTube embed URL")
    pdf_url: Optional[str] = Field(None, description="Optional attached PDF CDN URL")
    class_id: Optional[int] = Field(None, description="Target class id (null for all)")
    district: Optional[str] = Field(None, description="Target district")
    status: NewsStatus = Field("draft", description="draft | published | archived")
    is_pinned: bool = Field(False, description="Whether article is pinned")
    published_at: Optional[datetime] = Field(None, description="Publish date")


class NewsCreate(NewsBase):
    """Payload for creating a news article."""
    pass


class NewsUpdate(BaseModel):
    """Payload for updating a news article."""
    title: Optional[str] = Field(None, min_length=3, max_length=400)
    summary: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    thumbnail_url: Optional[str] = None
    thumbnail_alt: Optional[str] = None
    youtube_url: Optional[str] = None
    pdf_url: Optional[str] = None
    class_id: Optional[int] = None
    district: Optional[str] = None
    status: Optional[NewsStatus] = None
    is_pinned: Optional[bool] = None
    published_at: Optional[datetime] = None


class NewsOut(NewsBase):
    """Schema for returning news article details."""
    id: str
    slug: str
    view_count: int = 0
    created_at: datetime
    updated_at: datetime
    class_name: Optional[str] = None


class NewsListResponse(BaseModel):
    """List response for news articles."""
    data: List[NewsOut]
    total: int


class NewsDeleteResponse(BaseModel):
    """Response returned upon news article deletion."""
    id: str
    deleted: bool = True
    storage_deleted: bool = True
    message: str = "News article deleted successfully"