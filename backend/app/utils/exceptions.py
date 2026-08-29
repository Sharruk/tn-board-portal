"""
Shared exception utilities for the TN Board Portal API.

Centralises all HTTPException construction so route handlers
never construct error responses directly — they raise typed
exceptions from here, keeping routes paper-thin.
"""

from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Resource was not found in the database."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id '{identifier}' was not found.",
        )


class DatabaseError(HTTPException):
    """Unexpected error returned by Supabase."""

    def __init__(self, detail: str = "An unexpected database error occurred.") -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class ValidationError(HTTPException):
    """Request parameter failed validation."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class ForbiddenError(HTTPException):
    """User lacks permission to perform this action."""

    def __init__(self, detail: str = "Access forbidden.") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class UnauthorizedError(HTTPException):
    """Authentication required or invalid."""

    def __init__(self, detail: str = "Authentication required.") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

