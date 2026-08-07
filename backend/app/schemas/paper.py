"""
Pydantic schemas for the Papers domain.

Mirrors the complete `papers` table schema including all columns
added across migrations 001 → 016:

  papers columns:
    id, subject_id, exam_type, year, month, district, title,
    paper_type, file_path, public_url, youtube_url,
    original_filename, is_visible, status, download_count, created_at

  search_papers() RPC also returns joined columns:
    subject_name, class_id, class_name

Schema hierarchy:
  PaperBase          — raw DB columns
  PaperResponse      — single paper enriched (GET /papers/{id})
  PaperSummary       — list item (GET /papers, GET /papers/search)
  PaperListResponse  — paginated list wrapper
  PaperSearchResult  — search result (mirrors frontend SearchPage output)
  SearchResponse     — wrapper returned by GET /papers/search
  PaperSearchParams  — query params for /search (documented, not a Pydantic model)
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Paper type literals ───────────────────────────────────────────────────────

PaperType   = Literal["question", "answer_key"]
PaperStatus = Literal["draft", "published", "archived"]


# ── Base + core response ──────────────────────────────────────────────────────

class PaperBase(BaseModel):
    id: int = Field(..., description="Paper primary key")
    subject_id: int = Field(..., description="Foreign key → subjects.id")
    exam_type: str = Field(..., description="Exam category", examples=["Annual Exam"])
    year: int = Field(..., description="Academic year", examples=[2024])
    month: str | None = Field(None, description="Month the exam was held", examples=["July"])
    district: str | None = Field(None, description="TN district (nullable)", examples=["Chennai"])
    title: str = Field(..., description="Paper title")
    paper_type: PaperType = Field(..., description='"question" or "answer_key"')
    public_url: str | None = Field(None, description="Supabase Storage public CDN URL")
    youtube_url: str | None = Field(None, description="Optional YouTube embed URL")
    original_filename: str | None = Field(None, description="Original uploaded filename")
    is_visible: bool = Field(..., description="Legacy visibility flag")
    status: PaperStatus = Field(..., description="draft | published | archived")
    download_count: int = Field(default=0, description="Total download count")
    created_at: datetime = Field(..., description="Upload timestamp")


class PaperResponse(PaperBase):
    """
    Single paper with full subject + class join.
    Returned by GET /api/v1/papers/{id}.
    Mirrors getPaper() in frontend/src/services/papers.js.
    """

    # Joined from subjects
    subject_name: str | None = Field(None, description="Subject name")
    subject_slug: str | None = Field(None, description="Subject slug")
    is_practical: bool | None = Field(None, description="Is a practical subject")

    # Joined from classes (via subjects)
    class_id: int | None = Field(None, description="Parent class id")
    class_name: str | None = Field(None, description="Parent class name")
    class_slug: str | None = Field(None, description="Parent class slug")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 42,
                    "subject_id": 8,
                    "exam_type": "Annual Exam",
                    "year": 2024,
                    "month": None,
                    "district": None,
                    "title": "Class 10 Maths Annual Exam 2024",
                    "paper_type": "question",
                    "public_url": "https://your-project.supabase.co/storage/v1/object/public/papers/uuid.pdf",
                    "youtube_url": None,
                    "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
                    "is_visible": True,
                    "status": "published",
                    "download_count": 1234,
                    "created_at": "2024-03-15T10:30:00Z",
                    "subject_name": "Mathematics",
                    "subject_slug": "maths",
                    "is_practical": False,
                    "class_id": 10,
                    "class_name": "Class 10",
                    "class_slug": "10",
                }
            ]
        }
    }


class PaperSummary(BaseModel):
    """
    Lightweight paper item for list endpoints.
    Does NOT include file_path (internal storage key).
    Mirrors the shape returned by getRecentPapers / getPopularPapers.
    """

    id: int
    subject_id: int
    exam_type: str
    year: int
    month: str | None = None
    district: str | None = None
    title: str
    paper_type: PaperType
    public_url: str | None = None
    youtube_url: str | None = None
    original_filename: str | None = None
    status: PaperStatus
    download_count: int = 0
    created_at: datetime


class PaperListResponse(BaseModel):
    """Paginated list of papers."""

    data: list[PaperSummary]
    count: int = Field(..., description="Number of papers returned")
    limit: int = Field(..., description="Limit applied")


# ── Search result ─────────────────────────────────────────────────────────────

class PaperSearchResult(BaseModel):
    """
    Single paper search result.
    Mirrors the shape produced by frontend/src/services/search.js searchPapers().
    All fields come directly from the search_papers() Supabase RPC.
    """

    id: int
    title: str
    exam_type: str
    year: int
    month: str | None = None
    district: str | None = None
    paper_type: PaperType
    public_url: str | None = None
    original_filename: str | None = None
    subject_name: str
    class_name: str
    class_id: int
    status: PaperStatus
    download_count: int = 0
    created_at: datetime


class SearchResponse(BaseModel):
    """
    Response for GET /api/v1/papers/search.
    Wraps search results with metadata.
    """

    query: str = Field(..., description="The search term that was used")
    total: int = Field(..., description="Total results returned")
    results: list[PaperSearchResult]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "mathematics",
                    "total": 2,
                    "results": [
                        {
                            "id": 42,
                            "title": "Class 10 Maths Annual Exam 2024",
                            "exam_type": "Annual Exam",
                            "year": 2024,
                            "month": None,
                            "district": None,
                            "paper_type": "question",
                            "public_url": "https://...",
                            "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
                            "subject_name": "Mathematics",
                            "class_name": "Class 10",
                            "class_id": 10,
                            "status": "published",
                            "download_count": 1234,
                            "created_at": "2024-03-15T10:30:00Z",
                        }
                    ],
                }
            ]
        }
    }
