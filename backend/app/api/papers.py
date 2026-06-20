from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.models.models import Paper, Subject, Class
from app.schemas.schemas import PaperOut, PaperDetail, SearchResult, SearchResponse

router = APIRouter(tags=["Papers"])

EXAM_TYPES = [
    "Unit Test 1", "Unit Test 2", "Unit Test 3",
    "Quarterly Exam", "Half Yearly Exam",
    "Annual Exam", "Public Exam",
    "Practical Exam", "Model Exam",
]


@router.get("/exam-types")
def get_exam_types():
    return {"exam_types": EXAM_TYPES}


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
    return paper


@router.get("/search", response_model=SearchResponse)
def search_papers(
    q: str = Query(..., min_length=1, description="Search query"),
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

    search_term = f"%{q.lower()}%"
    from sqlalchemy import or_, func
    query = query.filter(
        or_(
            func.lower(Paper.title).like(search_term),
            func.lower(Paper.exam_type).like(search_term),
            func.lower(Subject.name).like(search_term),
        )
    )

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
            id=p.id,
            title=p.title,
            exam_type=p.exam_type,
            year=p.year,
            paper_type=p.paper_type,
            subject_name=p.subject.name,
            class_name=p.subject.class_.name,
            public_url=p.public_url,
        )
        for p in papers
    ]

    return SearchResponse(query=q, total=len(results), results=results)
