import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, computed_field


def _slugify(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'[\s_]+', '-', t)
    return re.sub(r'-+', '-', t).strip('-')


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
    class_id: Optional[int] = None
    class_name: Optional[str] = None

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
    download_count: int = 0
    created_at: datetime
    subject_id: int

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def slug(self) -> str:
        return f"{_slugify(self.title)}-{self.id}"


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

    @computed_field
    @property
    def slug(self) -> str:
        return f"{_slugify(self.title)}-{self.id}"


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]


# ── Admin Stats ────────────────────────────────────────────────────────────────

class AdminStats(BaseModel):
    total_papers: int
    total_downloads: int
    total_subjects: int
    total_classes: int
    visible_papers: int
    question_papers: int
    answer_keys: int
