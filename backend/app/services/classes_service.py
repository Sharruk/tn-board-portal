"""
Classes service — business logic for the classes domain.

This layer sits between routes and repositories.
It owns all business rules so they can be unit-tested
independently of HTTP and Supabase.

Current rules (Sprint 03):
  - list:       return all 4 classes ordered by id
  - get_by_id:  return one class or raise NotFoundError
"""

import logging

from supabase import Client

from app.repositories.classes_repository import ClassesRepository
from app.schemas.class_ import ClassListResponse, ClassResponse
from app.utils.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class ClassesService:
    """Business logic for the classes domain."""

    def __init__(self, db: Client) -> None:
        self._repo = ClassesRepository(db)

    # ------------------------------------------------------------------ #
    # Public interface (called by routes)
    # ------------------------------------------------------------------ #

    def list_classes(self) -> ClassListResponse:
        """Return all school classes with their subject counts."""
        logger.info("ClassesService.list_classes()")
        rows = self._repo.list_all()
        items = [ClassResponse(**row) for row in rows]
        return ClassListResponse(data=items, count=len(items))

    def get_class(self, class_id: int) -> ClassResponse:
        """
        Return a single class by id.

        Raises:
            NotFoundError: if no class with the given id exists.
        """
        logger.info("ClassesService.get_class(class_id=%s)", class_id)
        row = self._repo.get_by_id(class_id)
        if row is None:
            raise NotFoundError(resource="Class", identifier=class_id)
        return ClassResponse(**row)
