from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from app.database.database import get_db
from app.models.models import Admin, AuditLog, Paper, Subject, Class
from app.schemas.schemas import AdminOut, AuditLogOut, PaperOut, PaperUpdate, AdminStats
from app.services.auth import get_current_admin
from app.services.storage import save_file_locally, delete_file_locally
from app.services.analytics import get_analytics
from app.services.audit import log_action

router = APIRouter(prefix="/admin", tags=["Admin"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Admin identity ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=AdminOut)
def get_admin_me(current_admin: Admin = Depends(get_current_admin)):
    return current_admin


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStats)
def admin_stats(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    total_papers = db.query(Paper).count()
    total_downloads = db.query(func.sum(Paper.download_count)).scalar() or 0
    total_subjects = db.query(Subject).count()
    total_classes = db.query(Class).count()
    visible_papers = db.query(Paper).filter(Paper.is_visible == True).count()
    question_papers = db.query(Paper).filter(Paper.paper_type == "question").count()
    answer_keys = db.query(Paper).filter(Paper.paper_type == "answer_key").count()
    return AdminStats(
        total_papers=total_papers,
        total_downloads=total_downloads,
        total_subjects=total_subjects,
        total_classes=total_classes,
        visible_papers=visible_papers,
        question_papers=question_papers,
        answer_keys=answer_keys,
    )


# ── Papers CRUD ───────────────────────────────────────────────────────────────

@router.get("/papers", response_model=List[PaperOut])
def list_all_papers(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return db.query(Paper).order_by(Paper.created_at.desc()).all()


@router.post("/papers", response_model=PaperOut, status_code=201)
async def upload_paper(
    request: Request,
    subject_id: int = Form(...),
    exam_type: str = Form(...),
    year: int = Form(...),
    title: str = Form(...),
    paper_type: str = Form(...),
    youtube_url: Optional[str] = Form(None),
    is_bulk: bool = Form(False),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    if paper_type not in ("question", "answer_key"):
        raise HTTPException(status_code=400, detail="paper_type must be 'question' or 'answer_key'")

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="A PDF file is required.")

    duplicate = db.query(Paper).filter(
        Paper.subject_id == subject_id,
        Paper.title == title,
        Paper.year == year,
        Paper.exam_type == exam_type,
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A paper with the same title, subject, year, and exam type already exists.",
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

    action = "bulk_upload" if is_bulk else "upload"
    log_action(
        db,
        action=action,
        admin_id=current_admin.id,
        admin_email=current_admin.email or current_admin.username,
        target_paper_id=paper.id,
        details={"title": paper.title, "exam_type": exam_type, "year": year},
        ip_address=_client_ip(request),
    )

    return paper


@router.put("/papers/{paper_id}", response_model=PaperOut)
def update_paper(
    paper_id: int,
    request: Request,
    payload: PaperUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    old_values = {k: getattr(paper, k) for k in payload.model_dump(exclude_unset=True)}

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(paper, field, value)

    db.commit()
    db.refresh(paper)

    log_action(
        db,
        action="edit",
        admin_id=current_admin.id,
        admin_email=current_admin.email or current_admin.username,
        target_paper_id=paper.id,
        details={"title": paper.title, "changes": payload.model_dump(exclude_unset=True)},
        ip_address=_client_ip(request),
    )

    return paper


@router.delete("/papers/{paper_id}", status_code=204)
def delete_paper(
    paper_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    paper_title = paper.title
    paper_file = paper.file_path

    db.delete(paper)
    db.commit()

    if paper_file:
        delete_file_locally(paper_file)

    log_action(
        db,
        action="delete",
        admin_id=current_admin.id,
        admin_email=current_admin.email or current_admin.username,
        target_paper_id=paper_id,
        details={"title": paper_title},
        ip_address=_client_ip(request),
    )


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/search-analytics")
def search_analytics(_=Depends(get_current_admin)):
    return get_analytics()


# ── Audit Logs ────────────────────────────────────────────────────────────────

@router.get("/audit-logs", response_model=List[AuditLogOut])
def get_audit_logs(
    limit: int = 50,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        q = q.filter(AuditLog.action == action)
    return q.limit(limit).all()


# ── Recent uploads ────────────────────────────────────────────────────────────

@router.get("/recent-uploads")
def recent_uploads(
    limit: int = 20,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    papers = (
        db.query(Paper)
        .options(joinedload(Paper.subject).joinedload(Subject.class_))
        .order_by(Paper.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for p in papers:
        result.append({
            "id": p.id,
            "title": p.title,
            "exam_type": p.exam_type,
            "year": p.year,
            "paper_type": p.paper_type,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "subject_name": p.subject.name if p.subject else "",
            "class_name": p.subject.class_.name if p.subject and p.subject.class_ else "",
        })
    return result


# ── Content Status ────────────────────────────────────────────────────────────

@router.get("/content-status")
def content_status(
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    TRACKED = [
        "Annual Exam",
        "Half Yearly Exam",
        "Quarterly Exam",
        "Unit Test 1",
        "Unit Test 2",
        "Unit Test 3",
    ]

    classes = (
        db.query(Class)
        .options(joinedload(Class.subjects))
        .order_by(Class.id)
        .all()
    )
    papers = db.query(Paper).all()

    coverage_set = set()
    for p in papers:
        coverage_set.add((p.subject_id, p.exam_type))

    result = []
    for cls in classes:
        subjects_data = []
        for sub in cls.subjects:
            coverage = {et: (sub.id, et) in coverage_set for et in TRACKED}
            subjects_data.append({
                "id": sub.id,
                "name": sub.name,
                "coverage": coverage,
            })
        result.append({
            "id": cls.id,
            "name": cls.name,
            "subjects": subjects_data,
        })

    return {"exam_types": TRACKED, "classes": result}
