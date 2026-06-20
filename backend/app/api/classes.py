from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.models import Class
from app.schemas.schemas import ClassOut
from typing import List

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.get("", response_model=List[ClassOut])
def get_all_classes(db: Session = Depends(get_db)):
    classes = db.query(Class).order_by(Class.id).all()
    result = []
    for c in classes:
        result.append(ClassOut(
            id=c.id,
            name=c.name,
            slug=c.slug,
            subject_count=len(c.subjects),
        ))
    return result


@router.get("/{class_id}", response_model=ClassOut)
def get_class(class_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    c = db.query(Class).filter(Class.id == class_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassOut(id=c.id, name=c.name, slug=c.slug, subject_count=len(c.subjects))
