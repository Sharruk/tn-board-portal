"""
Pydantic schemas for Official Notices.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NoticeBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=300, description="Notice headline")
    category: str = Field(..., description="Notice category")
    class_id: Optional[int] = Field(None, description="Target class id (null for all classes)")
    year: int = Field(..., description="Academic year")
    description: Optional[str] = Field(None, description="Detailed description")
    file_path: Optional[str] = Field(None, description="Supabase storage path")
    public_url: Optional[str] = Field(None, description="Supabase storage public URL")
    file_type: Optional[str] = Field(None, description="File extension/type (pdf, image, etc.)")
    youtube_url: Optional[str] = Field(None, description="Optional YouTube embed URL")
    is_visible: bool = Field(True, description="Public visibility flag")
    is_pinned: bool = Field(False, description="Whether notice is pinned to top")
    expires_at: Optional[datetime] = Field(None, description="Expiry date after which notice is hidden")


class NoticeCreate(NoticeBase):
    """Payload for creating an official notice."""
    pass


class NoticeUpdate(BaseModel):
    """Payload for updating an official notice."""
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    category: Optional[str] = None
    class_id: Optional[int] = None
    year: Optional[int] = None
    description: Optional[str] = None
    file_path: Optional[str] = None
    public_url: Optional[str] = None
    file_type: Optional[str] = None
    youtube_url: Optional[str] = None
    is_visible: Optional[bool] = None
    is_pinned: Optional[bool] = None
    expires_at: Optional[datetime] = None


class NoticeOut(NoticeBase):
    """Schema for returning notice details."""
    id: int
    view_count: int = 0
    download_count: int = 0
    created_at: datetime
    updated_at: datetime
    class_name: Optional[str] = None


class NoticeListResponse(BaseModel):
    """Paginated or listed notices response."""
    data: List[NoticeOut]
    total: int


class NoticeDeleteResponse(BaseModel):
    """Response returned upon notice deletion."""
    id: int
    deleted: bool = True
    storage_deleted: bool = True
    message: str = "Notice deleted successfully"