from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from app.database.database import get_db
from app.models.models import Paper, Subject, Class
from app.schemas.schemas import PaperOut, PaperDetail, SubjectOut, SearchResult, SearchResponse
from app.services.analytics import track_search

router = APIRouter(tags=["Papers"])

EXAM_TYPES = [
    "Unit Test 1", "Unit Test 2", "Unit Test 3",
    "Quarterly Exam", "Half Yearly Exam",
    "Annual Exam", "Public Exam",
    "Practical Exam", "Model Exam",
]

SUBJECT_ALIASES = {
    "maths": "mathematics",
    "math": "mathematics",
    "phy": "physics",
    "chem": "chemistry",
    "bio": "biology",
    "sci": "science",
    "eng": "english",
    "eco": "economics",
    "acc": "accountancy",
    "hist": "history",
    "geo": "geography",
    "cs": "computer science",
    "comp": "computer science",
    "comm": "commerce",
    "qly": "quarterly",
    "qtly": "quarterly",
    "half": "half yearly",
    "hy": "half yearly",
    "annual": "annual exam",
    "pub": "public exam",
}


def _expand_query(q: str) -> List[str]:
    """Return a list of terms to OR-match (original + alias expansion)."""
    normalized = q.strip().lower()
    terms = [normalized]
    if normalized in SUBJECT_ALIASES:
        terms.append(SUBJECT_ALIASES[normalized])
    for word in normalized.split():
        if word in SUBJECT_ALIASES and SUBJECT_ALIASES[word] not in terms:
            terms.append(SUBJECT_ALIASES[word])
    return list(dict.fromkeys(terms))


def _build_subject_out(s: Subject) -> SubjectOut:
    return SubjectOut(
        id=s.id, name=s.name, slug=s.slug,
        is_practical=s.is_practical,
        class_id=s.class_.id,
        class_name=s.class_.name,
    )


def _build_paper_detail(paper: Paper) -> PaperDetail:
    subject_out = _build_subject_out(paper.subject) if paper.subject else None
    return PaperDetail(
        id=paper.id, title=paper.title, exam_type=paper.exam_type,
        year=paper.year, paper_type=paper.paper_type,
        public_url=paper.public_url, youtube_url=paper.youtube_url,
        is_visible=paper.is_visible, download_count=paper.download_count,
        created_at=paper.created_at, subject_id=paper.subject_id,
        subject=subject_out,
    )


@router.get("/exam-types")
def get_exam_types():
    return {"exam_types": EXAM_TYPES}


@router.get("/papers/recent", response_model=List[PaperOut])
def get_recent_papers(limit: int = 10, db: Session = Depends(get_db)):
    return (
        db.query(Paper)
        .filter(Paper.is_visible == True)
        .order_by(Paper.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/papers/popular", response_model=List[PaperOut])
def get_popular_papers(limit: int = 10, db: Session = Depends(get_db)):
    return (
        db.query(Paper)
        .filter(Paper.is_visible == True)
        .order_by(Paper.download_count.desc(), Paper.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/papers/by-slug/{slug}", response_model=PaperDetail)
def get_paper_by_slug(slug: str, db: Session = Depends(get_db)):
    """Look up a paper by its SEO slug (e.g. class-10-maths-annual-2024-5)."""
    parts = slug.rsplit('-', 1)
    if len(parts) != 2 or not parts[1].isdigit():
        raise HTTPException(status_code=404, detail="Paper not found")
    paper_id = int(parts[1])
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.is_visible == True).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _build_paper_detail(paper)


@router.get("/subjects/{subject_id}/papers", response_model=List[PaperOut])
def get_papers_for_subject(
    subject_id: int,
    exam_type: Optional[str] = None,
    paper_type: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    q = db.query(Paper).filter(Paper.subject_id == subject_id, Paper.is_visible == True)
    if exam_type:
        q = q.filter(Paper.exam_type == exam_type)
    if paper_type:
        q = q.filter(Paper.paper_type == paper_type)
    if year:
        q = q.filter(Paper.year == year)

    return q.order_by(Paper.year.desc()).all()


@router.get("/papers/{paper_id}", response_model=PaperDetail)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.is_visible == True).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _build_paper_detail(paper)


@router.post("/papers/{paper_id}/download", response_model=PaperOut)
def record_download(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.is_visible == True).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    paper.download_count = (paper.download_count or 0) + 1
    db.commit()
    db.refresh(paper)
    return paper


@router.get("/search", response_model=SearchResponse)
def search_papers(
    q: str = Query(..., min_length=1),
    class_id: Optional[int] = None,
    exam_type: Optional[str] = None,
    paper_type: Optional[str] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Paper)
        .join(Subject, Paper.subject_id == Subject.id)
        .join(Class, Subject.class_id == Class.id)
        .filter(Paper.is_visible == True)
    )

    terms = _expand_query(q)
    conditions = []
    for t in terms:
        like = f"%{t}%"
        conditions.extend([
            func.lower(Paper.title).like(like),
            func.lower(Paper.exam_type).like(like),
            func.lower(Subject.name).like(like),
            func.lower(Class.name).like(like),
        ])
    query = query.filter(or_(*conditions))

    if class_id:
        query = query.filter(Subject.class_id == class_id)
    if exam_type:
        query = query.filter(Paper.exam_type == exam_type)
    if paper_type:
        query = query.filter(Paper.paper_type == paper_type)
    if year:
        query = query.filter(Paper.year == year)

    papers = query.order_by(Paper.created_at.desc()).limit(50).all()
    results = [
        SearchResult(
            id=p.id, title=p.title, exam_type=p.exam_type,
            year=p.year, paper_type=p.paper_type,
            subject_name=p.subject.name,
            class_name=p.subject.class_.name,
            public_url=p.public_url,
        )
        for p in papers
    ]

    try:
        track_search(q, len(results))
    except Exception:
        pass

    return SearchResponse(query=q, total=len(results), results=results)
