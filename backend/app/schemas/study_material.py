"""
Pydantic schemas for the Study Materials domain.
Handles study resources, multi-file attachments, and external learning links.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl

MaterialStatus = Literal["draft", "published", "archived"]
MaterialMedium = Literal["tamil", "english", "both", "not_applicable"]
QuestionFormat = Literal["1_mark", "2_marks", "3_marks", "5_marks", "10_marks"]
FileType = Literal["pdf", "image", "word", "presentation", "spreadsheet", "video", "external_link", "other"]


# ── File schemas ──────────────────────────────────────────────────────────────

class MaterialFileBase(BaseModel):
    file_title: str = Field(..., min_length=1, max_length=255, description="Human readable attachment label")
    display_filename: str = Field(..., min_length=1, max_length=255, description="Suggested download filename")
    file_type: FileType = Field(default="pdf", description="Technical file format")
    mime_type: Optional[str] = Field(None, max_length=100, description="MIME content type")
    file_size: int = Field(default=0, description="File size in bytes (0 for external links)")
    bucket_name: Optional[str] = Field(None, description="Supabase Storage bucket name")
    storage_path: Optional[str] = Field(None, description="Stable object path inside storage bucket")
    external_url: Optional[str] = Field(None, max_length=1000, description="External URL for videos/links")
    sort_order: int = Field(default=0, description="Sort order within bundle")


class MaterialFileCreate(MaterialFileBase):
    pass


class MaterialFileOut(MaterialFileBase):
    id: UUID
    material_id: UUID
    download_count: int = 0
    created_at: datetime
    public_url: Optional[str] = Field(None, description="Resolved public CDN URL or signed preview URL")


# ── Core Study Material schemas ───────────────────────────────────────────────

class StudyMaterialBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Material headline / title")
    description: Optional[str] = Field(None, description="Detailed description and syllabus notes")
    class_id: int = Field(..., description="Target standard (9, 10, 11, 12)")
    subject_id: Optional[int] = Field(None, description="Target subject ID (None for class-level general resources)")
    category_id: Optional[int] = Field(None, description="Category FK (None for uncategorized general resources)")
    medium: MaterialMedium = Field(default="both", description="Language medium")
    question_formats: List[QuestionFormat] = Field(default_factory=list, description="Marking formats (empty = N/A)")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    academic_year: Optional[str] = Field(None, max_length=20, description="Academic year (e.g. 2024-2025)")
    author_name: Optional[str] = Field(None, max_length=150, description="Author or teacher attribution")
    author_organization: Optional[str] = Field(None, max_length=200, description="School, district forum, or publisher")
    status: MaterialStatus = Field(default="draft", description="draft | published | archived")


class StudyMaterialCreate(StudyMaterialBase):
    slug: Optional[str] = Field(None, max_length=300, description="Optional custom slug; auto-generated from title if omitted")
    download_filename: Optional[str] = Field(None, max_length=255, description="Custom student download filename (e.g. Class 10 Maths Notes.pdf)")
    files: List[MaterialFileCreate] = Field(default_factory=list, description="Initial attached files or external links")


class StudyMaterialUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    download_filename: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    class_id: Optional[int] = None
    subject_id: Optional[int] = None
    category_id: Optional[int] = None
    medium: Optional[MaterialMedium] = None
    question_formats: Optional[List[QuestionFormat]] = None
    tags: Optional[List[str]] = None
    academic_year: Optional[str] = None
    author_name: Optional[str] = None
    author_organization: Optional[str] = None
    status: Optional[MaterialStatus] = None


class MaterialStatusUpdate(BaseModel):
    status: MaterialStatus = Field(..., description="draft | published | archived")


class StudyMaterialSummary(BaseModel):
    """Lightweight summary for list views and cards."""
    id: UUID
    title: str
    slug: str
    class_id: int
    class_name: Optional[str] = None
    subject_id: Optional[int] = None
    subject_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    medium: MaterialMedium
    question_formats: List[QuestionFormat] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    academic_year: Optional[str] = None
    author_name: Optional[str] = None
    status: MaterialStatus
    file_count: int = 0
    total_size_bytes: int = 0
    view_count: int = 0
    download_count: int = 0
    created_at: datetime
    updated_at: datetime


class StudyMaterialOut(StudyMaterialBase):
    """Full detail response including all file attachments."""
    id: UUID
    slug: str
    class_name: Optional[str] = None
    subject_name: Optional[str] = None
    category_name: Optional[str] = None
    category_slug: Optional[str] = None
    view_count: int = 0
    download_count: int = 0
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    files: List[MaterialFileOut] = Field(default_factory=list)


class StudyMaterialListResponse(BaseModel):
    data: List[StudyMaterialSummary]
    total: int
    page: int = 1
    limit: int = 20


# ── Interaction schemas (Likes & Comments) ───────────────────────────────────

class StudyMaterialLikeResponse(BaseModel):
    material_id: UUID
    likes_count: int
    has_liked: bool


class StudyMaterialCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[str] = None
    author_avatar: Optional[str] = None


class StudyMaterialCommentOut(BaseModel):
    id: str
    material_id: UUID
    firebase_uid: str
    author_name: str
    author_avatar: Optional[str] = None
    parent_id: Optional[str] = None
    content: str
    is_deleted: bool = False
    created_at: datetime
    updated_at: datetime
    replies: List["StudyMaterialCommentOut"] = Field(default_factory=list)

