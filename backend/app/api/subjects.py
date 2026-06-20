from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.models.models import Subject, Class, Paper
from app.schemas.schemas import SubjectOut

router = APIRouter(tags=["Subjects"])


@router.get("/classes/{class_id}/subjects", response_model=List[SubjectOut])
def get_subjects_for_class(class_id: int, db: Session = Depends(get_db)):
    cls = db.query(Class).filter(Class.id == class_id).first()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    result = []
    for s in cls.subjects:
        count = db.query(Paper).filter(
            Paper.subject_id == s.id,
            Paper.is_visible == True
        ).count()
        result.append(SubjectOut(id=s.id, name=s.name, slug=s.slug,
                                 is_practical=s.is_practical, paper_count=count))
    return result


@router.get("/subjects/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: Session = Depends(get_db)):
    s = db.query(Subject).filter(Subject.id == subject_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Subject not found")
    count = db.query(Paper).filter(
        Paper.subject_id == s.id,
        Paper.is_visible == True
    ).count()
    return SubjectOut(id=s.id, name=s.name, slug=s.slug,
                      is_practical=s.is_practical, paper_count=count)
