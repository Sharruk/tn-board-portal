from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.models.models import Paper, Subject
from app.schemas.schemas import PaperOut, PaperUpdate
from app.services.auth import get_current_admin
from app.services.storage import save_file_locally, delete_file_locally

router = APIRouter(prefix="/admin", tags=["Admin"])


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

    file_path = None
    public_url = None

    if file and file.filename:
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
