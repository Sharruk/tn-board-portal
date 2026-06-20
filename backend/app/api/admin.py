from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database.database import get_db
from app.models.models import Paper, Subject, Class
from app.schemas.schemas import PaperOut, PaperUpdate, AdminStats
from app.services.auth import get_current_admin
from app.services.storage import save_file_locally, delete_file_locally
from app.services.analytics import get_analytics

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStats)
def admin_stats(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    total_papers = db.query(Paper).count()
    total_downloads = db.query(func.sum(Paper.download_count)).scalar() or 0
    total_subjects = db.query(Subject).count()
    total_classes = db.query(Class).count()
    visible_papers = db.query(Paper).filter(Paper.is_visible == True).count()
    question_papers = db.query(Paper).filter(Paper.paper_type == 'question').count()
    answer_keys = db.query(Paper).filter(Paper.paper_type == 'answer_key').count()
    return AdminStats(
        total_papers=total_papers,
        total_downloads=total_downloads,
        total_subjects=total_subjects,
        total_classes=total_classes,
        visible_papers=visible_papers,
        question_papers=question_papers,
        answer_keys=answer_keys,
    )


@router.get("/papers", response_model=List[PaperOut])
def list_all_papers(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return db.query(Paper).order_by(Paper.created_at.desc()).all()


@router.post("/papers", response_model=PaperOut, status_code=201)
async def upload_paper(
    subject_id: int = Form(...),
    exam_type: str = Form(...),
    year: int = Form(...),
    title: str = Form(...),
    paper_type: str = Form(...),
    youtube_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    if paper_type not in ("question", "answer_key"):
        raise HTTPException(status_code=400, detail="paper_type must be 'question' or 'answer_key'")

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="A PDF file is required.")

    # Duplicate detection
    duplicate = db.query(Paper).filter(
        Paper.subject_id == subject_id,
        Paper.title == title,
        Paper.year == year,
        Paper.exam_type == exam_type,
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A paper with the same title, subject, year, and exam type already exists."
        )

    file_path, public_url = await save_file_locally(file)

    paper = Paper(
        subject_id=subject_id,
        exam_type=exam_type,
        year=year,
        title=title,
        paper_type=paper_type,
        file_path=file_path,
        public_url=public_url,
        youtube_url=youtube_url or None,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.put("/papers/{paper_id}", response_model=PaperOut)
def update_paper(
    paper_id: int,
    payload: PaperUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)

    db.commit()
    db.refresh(paper)
    return paper


@router.delete("/papers/{paper_id}", status_code=204)
def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    if paper.file_path:
        delete_file_locally(paper.file_path)

    db.delete(paper)
    db.commit()


@router.get("/search-analytics")
def search_analytics(_=Depends(get_current_admin)):
    return get_analytics()
