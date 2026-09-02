"""
Pydantic schemas for the Submissions domain.

Tables:
  submissions       — one row per public material submission
  submission_files  — one row per uploaded file (FK → submissions)

Schema hierarchy:
  SubmissionFileOut    — a file attached to a submission (returned to admin)
  SubmissionCreate     — body parsed from multipart form (public POST)
  SubmissionOut        — single submission detail (admin GET)
  SubmissionListItem   — lightweight row for admin list view
  SubmissionListResponse — paginated list wrapper
  ApproveRequest       — body for POST /submissions/{id}/approve
  RejectRequest        — body for POST /submissions/{id}/reject
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field



# ── Status literal ────────────────────────────────────────────────────────────

SubmissionStatus = Literal["pending", "approved", "rejected"]


# ── File schema ───────────────────────────────────────────────────────────────

class SubmissionFileOut(BaseModel):
    """One file attached to a submission. Returned to admin only."""

    id: str = Field(..., description="File UUID primary key")
    submission_id: str = Field(..., description="Parent submission UUID")
    original_filename: str = Field(..., description="Sanitised original filename")
    storage_path: str = Field(..., description="Supabase Storage object key")
    public_url: str | None = Field(None, description="Public CDN URL")
    signed_url: str | None = Field(None, description="Short-lived signed URL for admin viewing")
    file_type: str = Field(..., description="File extension: pdf, doc, docx, jpg, jpeg, png")
    file_size: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="Upload timestamp")


# ── Submission output schemas ─────────────────────────────────────────────────

class SubmissionListItem(BaseModel):
    """
    Lightweight submission row for the admin list view.
    Does NOT include file details — call GET /submissions/{id} for those.
    """

    id: str
    publisher_name: str
    email: str
    firebase_uid: str | None = None
    details: str | None = None
    status: SubmissionStatus
    file_count: int = Field(default=0, description="Number of files attached")
    rejection_reason: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class SubmissionOut(BaseModel):
    """
    Full submission detail including file list.
    Returned by GET /api/v1/submissions/{id}.
    """

    id: str
    publisher_name: str
    email: str
    firebase_uid: str | None = None
    details: str | None = None
    status: SubmissionStatus
    rejection_reason: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    files: list[SubmissionFileOut] = Field(default_factory=list)


class SubmissionListResponse(BaseModel):
    """Paginated list of submissions for the admin view."""

    data: list[SubmissionListItem]
    count: int = Field(..., description="Number of submissions returned")
    status_filter: str | None = Field(None, description="Status filter applied, if any")


# ── Admin action request schemas ──────────────────────────────────────────────

class ApproveRequest(BaseModel):
    """
    Body for POST /api/v1/submissions/{id}/approve.

    The admin supplies the human-readable title, approved download filename,
    description, optional YouTube URL, and metadata (subject, exam type, year, paper type, month, district).
    """

    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Admin-entered human-readable title for the paper",
    )
    download_filename: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Approved download filename for students (e.g. Class10_Science_MonthlyTest_August2026_Chennai_QP.pdf)",
    )
    description: str | None = Field(
        None,
        max_length=2000,
        description="Editable description/notes for the published paper",
    )
    youtube_url: str | None = Field(
        None,
        max_length=500,
        description="Optional YouTube explanation video URL",
    )
    class_id: int | None = Field(None, description="Class ID (optional)")
    subject_id: int = Field(..., description="Subject FK — from the subjects table", gt=0)
    exam_type: str = Field(
        ...,
        description="Exam category (e.g. 'Annual Exam', 'First Mid Term Test')",
        min_length=1,
        max_length=100,
    )
    year: int = Field(..., description="Academic year", ge=2000, le=2100)
    paper_type: Literal["question", "answer_key"] = Field(
        ..., description='"question" or "answer_key"'
    )
    month: str | None = Field(None, description="Month the exam was held (optional)")
    district: str | None = Field(None, description="TN district (optional)")

    @classmethod
    def validate_youtube_link(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v = v.strip()
        if not any(domain in v.lower() for domain in ["youtube.com", "youtu.be"]):
            raise ValueError("Invalid YouTube URL. Must contain 'youtube.com' or 'youtu.be'.")
        return v


class RejectRequest(BaseModel):
    """Body for POST /api/v1/submissions/{id}/reject."""

    rejection_reason: str | None = Field(
        None,
        description="Optional reason for rejection (stored for admin reference only)",
        max_length=1000,
    )


# ── Public submission response ────────────────────────────────────────────────

class SubmissionCreateResponse(BaseModel):
    """
    Returned after a successful public submission.
    Minimal — only the id and status are exposed publicly.
    """

    id: str = Field(..., description="Submission UUID")
    status: SubmissionStatus = Field(..., description="Always 'pending' on creation")
    message: str = Field(
        default="Material submitted successfully. It will be reviewed before publication.",
        description="Human-readable confirmation message",
    )


class SubmissionDeleteResponse(BaseModel):
    """Returned after successfully deleting a submission."""

    submission_id: str = Field(..., description="Deleted submission UUID")
    deleted: bool = Field(default=True, description="Deletion success indicator")
    deleted_paper_ids: list[int] = Field(
        default_factory=list,
        description="IDs of associated published papers deleted along with the submission",
    )
    message: str = Field(
        default="Submission deleted successfully.",
        description="Human-readable confirmation message",
    )


# ── User Contributor Own Submissions ──────────────────────────────────────────

class UserSubmissionFile(BaseModel):
    """Lightweight file info for user contribution tracking."""

    id: str
    original_filename: str
    file_type: str
    file_size: int
    created_at: datetime


class UserSubmissionPaper(BaseModel):
    """Linked published paper details when approved."""

    id: int
    title: str
    subject_name: Optional[str] = None
    class_name: Optional[str] = None
    exam_type: Optional[str] = None
    year: Optional[int] = None
    paper_type: Optional[str] = None
    public_url: Optional[str] = None


class UserSubmissionItem(BaseModel):
    """Submission item returned in the My Contributions page."""

    id: str
    publisher_name: str
    details: Optional[str] = None
    status: SubmissionStatus
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    files: list[UserSubmissionFile] = Field(default_factory=list)
    published_papers: list[UserSubmissionPaper] = Field(default_factory=list)


class UserSubmissionsResponse(BaseModel):
    """Response containing authenticated user's submissions."""

    data: list[UserSubmissionItem] = Field(default_factory=list)
    total: int = Field(default=0)
