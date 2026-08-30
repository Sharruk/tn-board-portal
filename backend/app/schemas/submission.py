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
from typing import Literal

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

    The admin supplies the human-readable title, optional YouTube URL,
    and metadata (subject, exam type, year, paper type, month, district).
    """

    title: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Admin-entered human-readable title for the paper",
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
