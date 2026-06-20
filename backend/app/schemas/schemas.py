import re
import json
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
    paper_type: str
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


# ── Admin ──────────────────────────────────────────────────────────────────────

class AdminOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    last_login_at: Optional[datetime] = None
    failed_login_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    action: str
    admin_email: Optional[str] = None
    target_paper_id: Optional[int] = None
    target_details: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def details_parsed(self) -> Optional[dict]:
        if self.target_details:
            try:
                return json.loads(self.target_details)
            except Exception:
                pass
        return None


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
