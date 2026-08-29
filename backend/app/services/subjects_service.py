"""
Subjects service — business logic for the subjects domain.

This layer sits between routes and repositories.
It owns all business rules so they can be unit-tested
independently of HTTP and Supabase.

Current rules (Sprint 03):
  - list:          return all subjects, optionally filtered by class_id
  - get_by_id:     return one subject or raise NotFoundError
"""

import logging

from sqlalchemy.orm import Session

from app.repositories.subjects_repository import SubjectsRepository
from app.schemas.subject import SubjectListResponse, SubjectResponse
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class SubjectsService:
    """Business logic for the subjects domain."""

    def __init__(self, db: Session) -> None:
        self._repo = SubjectsRepository(db)


    # ------------------------------------------------------------------ #
    # Public interface (called by routes)
    # ------------------------------------------------------------------ #

    def list_subjects(self, class_id: int | None = None) -> SubjectListResponse:
        """
        Return subjects, optionally filtered by class_id.

        Args:
            class_id: When provided, only return subjects for that class.
                      When None, return all subjects across all classes.
        """
        logger.info("SubjectsService.list_subjects(class_id=%s)", class_id)
        if class_id is not None:
            rows = self._repo.list_by_class(class_id)
        else:
            rows = self._repo.list_all()

        items = [SubjectResponse(**row) for row in rows]
        return SubjectListResponse(data=items, count=len(items), class_id=class_id)

    def get_subject(self, subject_id: int) -> SubjectResponse:
        """
        Return a single subject by id.

        Raises:
            NotFoundError: if no subject with the given id exists.
        """
        logger.info("SubjectsService.get_subject(subject_id=%s)", subject_id)
        row = self._repo.get_by_id(subject_id)
        if row is None:
            raise NotFoundError(resource="Subject", identifier=subject_id)
        return SubjectResponse(**row)
