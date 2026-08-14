"""
Submissions endpoints.

Endpoints:
  POST /api/v1/submissions                            — public: create submission (multipart)
  GET  /api/v1/submissions                            — admin: list all submissions
  GET  /api/v1/submissions/{id}                       — admin: get submission detail
  POST /api/v1/submissions/{id}/approve               — admin: approve + create paper
  POST /api/v1/submissions/{id}/reject                — admin: reject submission
  POST /api/v1/submissions/{id}/restore               — admin: restore rejected → pending
  GET  /api/v1/submissions/files/{file_id}/download   — admin: proxy-download private file

Auth:
  POST /api/v1/submissions         → auth required (contributor role or higher)
  All other endpoints              → Firebase JWT required (admin only)

Admin auth mechanism:
  The caller must pass a valid Firebase JWT in the
  Authorization: Bearer <token> header.  The require_admin dependency
  verifies this token and raises HTTP 401/403 as appropriate.

Route responsibilities:
  - Accept and pass parameters to the service
  - Return response models
  - Nothing else

All business logic lives in SubmissionsService.
All database access lives in SubmissionsRepository.
"""

import logging
import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from supabase import Client

from app.db.supabase_client import get_supabase_admin_client
from app.dependencies.auth import require_admin, require_role
from app.schemas.submission import (
    ApproveRequest,
    RejectRequest,
    SubmissionCreateResponse,
    SubmissionListResponse,
    SubmissionOut,
)
from app.services.submissions_service import SubmissionsService
from app.utils.exceptions import NotFoundError, DatabaseError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/submissions", tags=["Submissions"])


# ── POST /api/v1/submissions — authenticated (contributor or higher) ──────────


@router.post(
    "",
    response_model=SubmissionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit educational material",
    description=(
        "Authenticated endpoint. Accepts a multipart form with contributor details and "
        "up to 5 files (PDF, Word, or image). "
        "The submission is stored with status='pending' for admin review.\\n\\n"
        "**Auth required.** Submissions do NOT immediately appear on the public site."
    ),
    responses={
        201: {"description": "Submission created, pending admin review"},
        422: {"description": "Validation error (missing fields, bad file type, file too large, etc.)"},
    },
)
async def create_submission(
    publisher_name: Annotated[str, Form(description="Contributor or publisher name")],
    files: Annotated[
        list[UploadFile],
        File(description="One or more files (PDF, DOC, DOCX, JPG, PNG). Max 5 files, 25 MB each."),
    ],
    details: Annotated[
        str | None,
        Form(description="Optional description or additional details"),
    ] = None,
    current_user: dict = Depends(require_role(["USER", "CONTRIBUTOR", "ADMIN", "SUPER_ADMIN"])),
    admin_db: Client = Depends(get_supabase_admin_client),
) -> SubmissionCreateResponse:
    """
    Create a new material submission.
    Uses the admin Supabase client because file uploads to the private
    submissions bucket require service-role permissions, and inserting
    then returning the row (select) bypasses the anon read restriction.
    """
    service = SubmissionsService(admin_db)
    return await service.create_submission(
        publisher_name=publisher_name,
        email=current_user.get("email"),
        firebase_uid=current_user.get("firebase_uid"),
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
    current_user: dict = Depends(require_admin),
    admin_db: Client = Depends(get_supabase_admin_client),
) -> SubmissionListResponse:
    """Return all submissions for the admin review UI."""
    service = SubmissionsService(admin_db)
    return service.list_submissions(status=status_filter, limit=limit)


# ── GET /api/v1/submissions/files/{file_id}/download — admin ─────────────────
#
# NOTE: This route MUST be declared BEFORE /{submission_id} so that FastAPI
# matches /submissions/files/… before it tries to capture 'files' as a
# {submission_id} path parameter.


@router.get(
    "/files/{file_id}/download",
    summary="Download a private submission file (admin)",
    description=(
        "Admin only. Proxies the private Supabase Storage file through the backend "
        "so the browser receives a proper Content-Disposition: attachment response.\\n\\n"
        "The HTML `download` attribute is silently ignored by browsers for cross-origin "
        "URLs, which is why signed URLs cannot be used for downloads directly. "
        "This endpoint solves that by streaming the file through the backend.\\n\\n"
        "The service-role key is never exposed to the browser."
    ),
    responses={
        200: {"description": "File bytes with Content-Disposition: attachment"},
        401: {"description": "No auth token provided"},
        403: {"description": "Invalid or expired token"},
        404: {"description": "File not found"},
        500: {"description": "Storage retrieval failed"},
    },
)
async def download_submission_file(
    file_id: str,
    current_user: dict = Depends(require_admin),
    admin_db: Client = Depends(get_supabase_admin_client),
) -> Response:
    """
    Proxy-download a submission file from the private Supabase bucket.

    Returns the raw bytes with:
      Content-Type:        <appropriate MIME type>
      Content-Disposition: attachment; filename="<original_filename>"

    The browser will save the file locally regardless of origin.
    """
    service = SubmissionsService(admin_db)
    try:
        file_bytes, content_type, original_filename = service.download_file(file_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission file '{file_id}' not found.",
        )
    except (DatabaseError, RuntimeError) as exc:
        logger.error("Download proxy failed for file_id=%s: %s", file_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve the file from storage.",
        )

    # RFC 5987 encoding for non-ASCII filenames
    encoded_name = urllib.parse.quote(original_filename, safe="")
    disposition = f'attachment; filename="{original_filename}"; filename*=UTF-8\'\'{encoded_name}'

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": disposition},
    )


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
    current_user: dict = Depends(require_admin),
    admin_db: Client = Depends(get_supabase_admin_client),
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
    current_user: dict = Depends(require_admin),
    admin_db: Client = Depends(get_supabase_admin_client),
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
        "The submission status is set to `rejected` and `reviewed_at` is set to now.\\n\\n"
        "A rejected submission can later be restored to `pending` via the "
        "`POST /submissions/{id}/restore` endpoint."
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
    current_user: dict = Depends(require_admin),
    admin_db: Client = Depends(get_supabase_admin_client),
) -> dict:
    """Reject a pending submission."""
    service = SubmissionsService(admin_db)
    return service.reject_submission(submission_id, req)


# ── POST /api/v1/submissions/{id}/restore — admin ────────────────────────────


@router.post(
    "/{submission_id}/restore",
    status_code=status.HTTP_200_OK,
    summary="Restore a rejected submission to pending (admin)",
    description=(
        "Admin only. Moves a `rejected` submission back to `pending` so it can "
        "be reviewed and approved.\\n\\n"
        "Clears `rejection_reason` and `reviewed_at`.\\n\\n"
        "Only `rejected` submissions can be restored. "
        "`approved` submissions cannot be restored (they are already published).\\n\\n"
        "State machine: REJECTED → PENDING → APPROVED"
    ),
    responses={
        200: {"description": "Submission restored to pending"},
        401: {"description": "No auth token"},
        403: {"description": "Invalid token"},
        404: {"description": "Submission not found"},
        422: {"description": "Submission is not rejected"},
    },
)
async def restore_submission(
    submission_id: str,
    current_user: dict = Depends(require_admin),
    admin_db: Client = Depends(get_supabase_admin_client),
) -> dict:
    """Restore a rejected submission back to pending for re-review."""
    service = SubmissionsService(admin_db)
    return service.restore_submission(submission_id)
