"""
Classes endpoints — GET /api/v1/classes and GET /api/v1/classes/{id}

Route layer responsibilities:
  - Validate path/query parameters (FastAPI does this via type hints)
  - Call the service
  - Return the response model
  - Nothing else

All business logic lives in ClassesService.
All database access lives in ClassesRepository.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.supabase import get_db
from app.schemas.class_ import ClassListResponse, ClassResponse
from app.services.classes_service import ClassesService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.get(
    "",
    response_model=ClassListResponse,
    summary="List all classes",
    description=(
        "Returns all four Tamil Nadu State Board school classes (9, 10, 11, 12) "
        "with the number of subjects in each class."
    ),
)
async def list_classes(db: Session = Depends(get_db)) -> ClassListResponse:
    """Return all school classes ordered by class number."""
    service = ClassesService(db)
    return service.list_classes()


@router.get(
    "/{class_id}",
    response_model=ClassResponse,
    summary="Get a single class",
    description="Returns one class by its numeric id (9, 10, 11, or 12).",
    responses={
        404: {"description": "Class not found"},
    },
)
async def get_class(class_id: int, db: Session = Depends(get_db)) -> ClassResponse:
    """Return a single class by its primary key."""
    service = ClassesService(db)

    return service.get_class(class_id)
