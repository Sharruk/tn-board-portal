"""
Subjects endpoints — GET /api/v1/subjects and GET /api/v1/subjects/{id}

Route layer responsibilities:
  - Validate path/query parameters (FastAPI does this via type hints)
  - Call the service
  - Return the response model
  - Nothing else

All business logic lives in SubjectsService.
All database access lives in SubjectsRepository.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.supabase import get_db
from app.schemas.subject import SubjectListResponse, SubjectResponse
from app.services.subjects_service import SubjectsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get(
    "",
    response_model=SubjectListResponse,
    summary="List subjects",
    description=(
        "Returns all subjects. "
        "Pass `class_id` to filter by class (e.g. `?class_id=10` for Class 10 subjects only)."
    ),
)
async def list_subjects(
    class_id: Annotated[
        int | None,
        Query(
            description="Filter subjects by class id (9, 10, 11, or 12)",
            examples=[10],
        ),
    ] = None,
    db: Session = Depends(get_db),
) -> SubjectListResponse:
    """Return all subjects, optionally filtered by class_id."""
    service = SubjectsService(db)
    return service.list_subjects(class_id=class_id)


@router.get(
    "/{subject_id}",
    response_model=SubjectResponse,
    summary="Get a single subject",
    description="Returns one subject by its numeric id, including parent class information.",
    responses={
        404: {"description": "Subject not found"},
    },
)
async def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
) -> SubjectResponse:
    """Return a single subject by its primary key."""
    service = SubjectsService(db)

    return service.get_subject(subject_id)
