"""
Submissions endpoints.

Endpoints:
  POST /api/v1/submissions                       — public: create submission (multipart)
  GET  /api/v1/submissions                       — admin: list all submissions
  GET  /api/v1/submissions/{id}                  — admin: get submission detail
  POST /api/v1/submissions/{id}/approve          — admin: approve + create paper
  POST /api/v1/submissions/{id}/reject           — admin: reject submission

Auth:
  POST /api/v1/submissions         → NO auth required (public form)
  All other endpoints              → Supabase JWT required (admin only)

Admin auth mechanism:
  The caller must pass a valid Supabase session JWT in the
  Authorization: Bearer <token> header.  The get_admin_db dependency
  verifies this token by calling supabase.auth.get_user() and raises
  HTTP 401 if the token is missing/invalid, or HTTP 403 if the user
  is not authenticated (no valid session).

Route responsibilities:
  - Accept and pass parameters to the service
  - Return response models
  - Nothing else

All business logic lives in SubmissionsService.
All database access lives in SubmissionsRepository.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from supabase import Client

from app.db.supabase_client import get_supabase_admin_client
from app.dependencies.supabase import get_db
from app.schemas.submission import (
    ApproveRequest,
    RejectRequest,
    SubmissionCreateResponse,
    SubmissionListResponse,
    SubmissionOut,
)
from app.services.submissions_service import SubmissionsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/submissions", tags=["Submissions"])



async def get_admin_db(
    authorization: Annotated[str | None, Header()] = None,
) -> Client:
    """
    Verify a Supabase JWT from the Authorization: Bearer header.

    Raises HTTP 401 if no token is provided.
    Raises HTTP 403 if the token is invalid or the user is not authenticated.

    Returns the SERVICE ROLE client so admin operations bypass RLS.
    This is safe because we have already verified the caller is authenticated.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Provide Authorization: Bearer <token>.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    # Verify the token using the anon client's auth module
    # (get_user validates the JWT against Supabase Auth)
    try:
        anon_client = get_supabase_admin_client()
        user_response = anon_client.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired admin token.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Admin token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired admin token.",
        ) from exc

    # Return the service role client for full DB access
    return get_supabase_admin_client()


# ── POST /api/v1/submissions — public ────────────────────────────────────────


@router.post(
    "",
    response_model=SubmissionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit educational material",
    description=(
        "Public endpoint. Accepts a multipart form with contributor details and "
        "up to 5 files (PDF, Word, or image). "
        "The submission is stored with status='pending' for admin review.\\n\\n"
        "**No auth required.** Submissions do NOT immediately appear on the public site."
    ),
    responses={
        201: {"description": "Submission created, pending admin review"},
        422: {"description": "Validation error (missing fields, bad file type, file too large, etc.)"},
    },
)
async def create_submission(
    publisher_name: Annotated[str, Form(description="Contributor or publisher name")],
    email: Annotated[str, Form(description="Contact email address")],
    files: Annotated[
        list[UploadFile],
        File(description="One or more files (PDF, DOC, DOCX, JPG, PNG). Max 5 files, 25 MB each."),
    ],
    details: Annotated[
        str | None,
        Form(description="Optional description or additional details"),
    ] = None,
    db: Client = Depends(get_db),
) -> SubmissionCreateResponse:
    """
    Create a new material submission.
    Uses the anon Supabase client — RLS restricts anon to INSERT only.
    """
    service = SubmissionsService(db)
    return await service.create_submission(
        publisher_name=publisher_name,
        email=email,
        details=details,
        files=files,
    )


# ── GET /api/v1/submissions — admin ──────────────────────────────────────────


@router.get(
    "",
    response_model=SubmissionListResponse,
    summary="List material submissions (admin)",
    description=(
        "Admin only. Returns submissions ordered by submitted date (newest first).\\n\\n"
        "Use the `status` query param to filter: `pending`, `approved`, or `rejected`."
    ),
    responses={
        200: {"description": "List of submissions"},
        401: {"description": "No auth token provided"},
        403: {"description": "Invalid or expired token"},
    },
)
async def list_submissions(
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by status: pending | approved | rejected"),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Max submissions to return", ge=1, le=200),
    ] = 50,
    admin_db: Client = Depends(get_admin_db),
) -> SubmissionListResponse:
    """Return all submissions for the admin review UI."""
    service = SubmissionsService(admin_db)
    return service.list_submissions(status=status_filter, limit=limit)


# ── GET /api/v1/submissions/{id} — admin ─────────────────────────────────────


@router.get(
    "/{submission_id}",
    response_model=SubmissionOut,
    summary="Get submission detail (admin)",
    description=(
        "Admin only. Returns one submission with its full file list.\\n\\n"
        "Use this to inspect files before approving or rejecting."
    ),
    responses={
        200: {"description": "Submission detail with files"},
        401: {"description": "No auth token provided"},
        403: {"description": "Invalid or expired token"},
        404: {"description": "Submission not found"},
    },
)
async def get_submission(
    submission_id: str,
    admin_db: Client = Depends(get_admin_db),
) -> SubmissionOut:
    """Return one submission with its file list."""
    service = SubmissionsService(admin_db)
    return service.get_submission(submission_id)


# ── POST /api/v1/submissions/{id}/approve — admin ────────────────────────────


@router.post(
    "/{submission_id}/approve",
    status_code=status.HTTP_200_OK,
    summary="Approve a submission (admin)",
    description=(
        "Admin only. Approves a pending submission and creates one published "
        "paper record in the `papers` table for each submitted file.\\n\\n"
        "The request body must supply `subject_id`, `exam_type`, `year`, and "
        "`paper_type` — the admin fills these in at approval time because the "
        "public form does not collect subject/class information.\\n\\n"
        "The submission status is set to `approved` and `reviewed_at` is set to now."
    ),
    responses={
        200: {"description": "Approved — paper(s) created"},
        401: {"description": "No auth token"},
        403: {"description": "Invalid token"},
        404: {"description": "Submission not found"},
        422: {"description": "Submission is not pending, or validation error"},
    },
)
async def approve_submission(
    submission_id: str,
    req: ApproveRequest,
    admin_db: Client = Depends(get_admin_db),
) -> dict:
    """Approve a pending submission and create paper records."""
    service = SubmissionsService(admin_db)
    return service.approve_submission(submission_id, req)


# ── POST /api/v1/submissions/{id}/reject — admin ─────────────────────────────


@router.post(
    "/{submission_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject a submission (admin)",
    description=(
        "Admin only. Rejects a pending submission.\\n\\n"
        "No paper record is created. The uploaded files remain in storage. "
        "An optional `rejection_reason` can be stored for admin reference.\\n\\n"
        "The submission status is set to `rejected` and `reviewed_at` is set to now."
    ),
    responses={
        200: {"description": "Rejected — no paper created"},
        401: {"description": "No auth token"},
        403: {"description": "Invalid token"},
        404: {"description": "Submission not found"},
        422: {"description": "Submission is not pending"},
    },
)
async def reject_submission(
    submission_id: str,
    req: RejectRequest,
    admin_db: Client = Depends(get_admin_db),
) -> dict:
    """Reject a pending submission."""
    service = SubmissionsService(admin_db)
    return service.reject_submission(submission_id, req)
