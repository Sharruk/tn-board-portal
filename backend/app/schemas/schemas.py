from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── Class ─────────────────────────────────────────────────────────────────────

class ClassOut(BaseModel):
    id: int
    name: str
    slug: str
    subject_count: Optional[int] = 0

    model_config = {"from_attributes": True}


# ── Subject ────────────────────────────────────────────────────────────────────

class SubjectOut(BaseModel):
    id: int
    name: str
    slug: str
    is_practical: bool
    paper_count: Optional[int] = 0

    model_config = {"from_attributes": True}


# ── Paper ──────────────────────────────────────────────────────────────────────

class PaperOut(BaseModel):
    id: int
    title: str
    exam_type: str
    year: int
    paper_type: str          # "question" | "answer_key"
    public_url: Optional[str]
    youtube_url: Optional[str]
    is_visible: bool
    created_at: datetime
    subject_id: int

    model_config = {"from_attributes": True}


class PaperDetail(PaperOut):
    subject: Optional[SubjectOut] = None


class PaperCreate(BaseModel):
    subject_id: int
    exam_type: str
    year: int
    title: str
    paper_type: str
    youtube_url: Optional[str] = None


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    exam_type: Optional[str] = None
    year: Optional[int] = None
    youtube_url: Optional[str] = None
    is_visible: Optional[bool] = None


# ── Auth ───────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Search ─────────────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    id: int
    title: str
    exam_type: str
    year: int
    paper_type: str
    subject_name: str
    class_name: str
    public_url: Optional[str]

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]
