"""
Submissions service — business logic for the material submission workflow.

Sits between routes and the repository.
All validation, security checks, and workflow logic live here.

Rules enforced:
  - File count limit (MAX_FILES_PER_SUBMISSION)
  - File size limit (MAX_FILE_SIZE_BYTES)
  - File type allowlist (ALLOWED_EXTENSIONS)
  - Email format is validated at the Pydantic schema level (EmailStr)
  - Only pending submissions can be approved or rejected
  - Admin JWT verification is done at the route level (not here)
  - Pending submissions are never returned by public paper endpoints
    (the papers repository already filters by is_visible = True)
"""

import logging
import re
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.repositories.submissions_repository import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    MAX_FILES_PER_SUBMISSION,
    SubmissionsRepository,
)
from app.schemas.submission import (
    ApproveRequest,
    RejectRequest,
    SubmissionCreateResponse,
    SubmissionDeleteResponse,
    SubmissionListItem,
    SubmissionListResponse,
    SubmissionOut,
    SubmissionFileOut,
    UserSubmissionFile,
    UserSubmissionPaper,
    UserSubmissionItem,
    UserSubmissionsResponse,
)
from app.utils.exceptions import DatabaseError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Characters allowed in the stored original filename (for display only)
_SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._\- ]")

DEFAULT_THANK_YOU_MESSAGE: str = (
    "🎉 Your contribution is now public!\n"
    "Thank you for contributing to the TN Board community. Your contribution may help another student prepare better. ❤️"
)

# MIME type map for file extension → Content-Type header
_EXT_TO_MIME: dict[str, str] = {
    "pdf":  "application/pdf",
    "doc":  "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
}



def _sanitise_filename(name: str) -> str:
    """Strip unsafe characters from an original filename for safe display/storage."""
    base = name.strip()
    safe = _SAFE_FILENAME_RE.sub("_", base)
    return safe[:255] if safe else "unnamed"


class SubmissionsService:
    """Business logic for the material submission domain."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._repo = SubmissionsRepository(db, storage=storage)

    # ------------------------------------------------------------------ #
    # PUBLIC: Create a new submission
    # POST /api/v1/submissions
    # ------------------------------------------------------------------ #

    async def create_submission(
        self,
        publisher_name: str,
        email: str,
        firebase_uid: str,
        details: str | None,
        files: list[UploadFile],
    ) -> SubmissionCreateResponse:
        """
        Validate inputs, create submission row, upload files.

        Raises ValidationError for any constraint violation.
        Raises DatabaseError if Supabase operations fail.
        """
        logger.info(
            "SubmissionsService.create_submission(email=%s, file_count=%s)",
            email,
            len(files),
        )

        # ── Validate publisher name ─────────────────────────────────────
        clean_publisher_name = (publisher_name or "").strip()
        if not (2 <= len(clean_publisher_name) <= 50):
            raise ValidationError("Publisher name must be between 2 and 50 characters.")

        # ── Validate file count ──────────────────────────────────────────
        if not files:
            raise ValidationError("At least one file is required.")
        if len(files) > MAX_FILES_PER_SUBMISSION:
            raise ValidationError(
                f"Maximum {MAX_FILES_PER_SUBMISSION} files allowed per submission."
            )

        # ── Validate each file (type + size) ─────────────────────────────
        validated: list[tuple[str, bytes, str, str, int]] = []
        for upload in files:
            original_name = upload.filename or "upload"
            ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationError(
                    f"File '{original_name}' has an unsupported type '{ext}'. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
                )

            content = await upload.read()
            size = len(content)

            if size == 0:
                raise ValidationError(f"File '{original_name}' is empty.")

            if size > MAX_FILE_SIZE_BYTES:
                mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
                raise ValidationError(
                    f"File '{original_name}' exceeds the {mb} MB size limit "
                    f"({size / (1024 * 1024):.1f} MB)."
                )

            content_type = upload.content_type or "application/octet-stream"
            safe_name = _sanitise_filename(original_name)
            validated.append((safe_name, content, content_type, ext, size))

        # ── Create submission row ────────────────────────────────────────
        try:
            sub = self._repo.create_submission(
                publisher_name=clean_publisher_name,
                email=email.strip().lower(),
                firebase_uid=firebase_uid,
                details=details.strip() if details else None,
            )
        except Exception as exc:
            logger.error("Failed to create submission: %s", exc)
            raise DatabaseError("Failed to create submission. Please try again.") from exc

        # ── Synchronize canonical user display_name if authenticated ────
        if firebase_uid:
            try:
                from app.repositories.user_profile_repository import UserProfileRepository
                UserProfileRepository(self._db).update_display_name(firebase_uid, clean_publisher_name)
            except Exception as exc:
                logger.warning("Could not sync display_name for user %s: %s", firebase_uid, exc)

        submission_id = sub["id"]

        # ── Upload files ──────────────────────────────────────────────────
        try:
            for safe_name, content, content_type, ext, size in validated:
                self._repo.upload_file(
                    submission_id=submission_id,
                    filename=safe_name,
                    content=content,
                    content_type=content_type,
                    file_size=size,
                    ext=ext,
                )
        except Exception as exc:
            logger.error(
                "File upload failed for submission %s: %s", submission_id, exc
            )
            # The submission row exists but files failed — surface a clear error
            raise DatabaseError(
                "Submission was created but file upload failed. Please try again."
            ) from exc

        logger.info("Submission %s created successfully", submission_id)
        return SubmissionCreateResponse(id=submission_id, status="pending")

    # ------------------------------------------------------------------ #
    # ADMIN: List submissions
    # GET /api/v1/submissions
    # ------------------------------------------------------------------ #

    def list_submissions(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> SubmissionListResponse:
        """
        Return submissions for the admin view, with file counts.

        Args:
            status: Optional filter — 'pending' | 'approved' | 'rejected'
            limit:  Max rows (default 50).
        """
        logger.info(
            "SubmissionsService.list_submissions(status=%s, limit=%s)",
            status,
            limit,
        )

        if status and status not in ("pending", "approved", "rejected"):
            raise ValidationError(
                f"Invalid status filter '{status}'. Must be pending, approved, or rejected."
            )

        rows = self._repo.list_submissions(status=status, limit=limit)

        # Fetch file counts in one round-trip
        ids = [r["id"] for r in rows]
        counts = self._repo.count_files_for_submissions(ids)

        items = [
            SubmissionListItem(
                **row,
                file_count=counts.get(row["id"], 0),
            )
            for row in rows
        ]

        return SubmissionListResponse(
            data=items,
            count=len(items),
            status_filter=status,
        )

    # ------------------------------------------------------------------ #
    # ADMIN: Get single submission
    # GET /api/v1/submissions/{id}
    # ------------------------------------------------------------------ #

    def get_submission(self, submission_id: str) -> SubmissionOut:
        """
        Return one submission with its file list.
        Raises NotFoundError if the submission does not exist.
        """
        logger.info(
            "SubmissionsService.get_submission(submission_id=%s)", submission_id
        )

        sub = self._repo.get_by_id(submission_id)
        if sub is None:
            raise NotFoundError(resource="Submission", identifier=submission_id)

        files = self._repo.get_files(submission_id)
        file_objects = [SubmissionFileOut(**f) for f in files]

        return SubmissionOut(**sub, files=file_objects)

    # ------------------------------------------------------------------ #
    # ADMIN: Approve a submission
    # POST /api/v1/submissions/{id}/approve
    # ------------------------------------------------------------------ #

    async def approve_submission(
        self,
        submission_id: str,
        req: ApproveRequest,
        prepared_file: UploadFile | tuple[str, bytes, str] | None = None,
    ) -> dict[str, Any]:
        """
        Approve a pending submission:
          1. Load submission — raise 404 if not found
          2. Verify status == 'pending'
          3. If prepared_file is provided:
             - Validate it and create one paper record directly from the prepared file
             - Original submission files remain preserved in private bucket
             If prepared_file is NOT provided:
             - Create one paper record per file in the original submission_files
          4. Update submission status → 'approved', set thank_you_message and reviewed_at

        Returns a dict with the submission id, status, paper_ids, and thank_you_message.
        Raises ValidationError if submission is not pending or file is invalid.
        """
        logger.info(
            "SubmissionsService.approve_submission(submission_id=%s, has_prepared_file=%s)",
            submission_id,
            prepared_file is not None,
        )

        sub = self._repo.get_by_id(submission_id)
        if sub is None:
            raise NotFoundError(resource="Submission", identifier=submission_id)

        if sub["status"] != "pending":
            raise ValidationError(
                f"Submission is already '{sub['status']}' — only pending submissions can be approved."
            )

        # Validate YouTube URL if provided
        youtube_url = None
        if req.youtube_url and req.youtube_url.strip():
            try:
                youtube_url = ApproveRequest.validate_youtube_link(req.youtube_url)
            except ValueError as e:
                raise ValidationError(str(e))

        paper_ids: list[int] = []

        # ── PATH A: Admin-Prepared File Upload ──────────────────────────
        if prepared_file is not None:
            if isinstance(prepared_file, UploadFile):
                raw_filename = prepared_file.filename or "prepared.pdf"
                content = await prepared_file.read()
                content_type = prepared_file.content_type or "application/pdf"
            elif isinstance(prepared_file, tuple):
                raw_filename, content, content_type = prepared_file
            else:
                raise ValidationError("Invalid prepared file object.")

            size = len(content)
            if size == 0:
                raise ValidationError("Prepared file is empty.")
            if size > MAX_FILE_SIZE_BYTES:
                mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
                raise ValidationError(
                    f"Prepared file exceeds the {mb} MB size limit ({size / (1024 * 1024):.1f} MB)."
                )

            ext = raw_filename.rsplit(".", 1)[-1].lower() if "." in raw_filename else "pdf"
            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationError(
                    f"Prepared file has unsupported extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
                )

            try:
                paper = self._repo.create_paper_from_prepared_file(
                    file_bytes=content,
                    subject_id=req.subject_id,
                    exam_type=req.exam_type,
                    year=req.year,
                    paper_type=req.paper_type,
                    month=req.month,
                    district=req.district,
                    submission=sub,
                    title=req.title,
                    download_filename=req.download_filename,
                    description=req.description,
                    youtube_url=youtube_url,
                    file_type=ext,
                )
                paper_ids.append(paper["id"])
            except Exception as exc:
                logger.exception(
                    "Failed to create paper from prepared file for submission %s: %s",
                    submission_id,
                    exc,
                )
                err_msg = str(exc).strip()
                if "duplicate key" in err_msg.lower() or "unique constraint" in err_msg.lower():
                    clean_reason = "A paper with this title, subject, year, and exam type already exists."
                else:
                    clean_reason = err_msg.split("\n")[0]
                raise DatabaseError(
                    f"Failed to publish prepared paper: {clean_reason}"
                ) from exc

        # ── PATH B: Original Contributor Uploaded File(s) ───────────────
        else:
            files = self._repo.get_files(submission_id)
            if not files:
                raise ValidationError(
                    "Submission has no files — cannot approve a submission without files."
                )

            for file_row in files:
                try:
                    paper = self._repo.create_paper_from_file(
                        file_row=file_row,
                        subject_id=req.subject_id,
                        exam_type=req.exam_type,
                        year=req.year,
                        paper_type=req.paper_type,
                        month=req.month,
                        district=req.district,
                        submission=sub,
                        title=req.title,
                        download_filename=req.download_filename,
                        description=req.description,
                        youtube_url=youtube_url,
                    )
                    paper_ids.append(paper["id"])
                except Exception as exc:
                    logger.exception(
                        "Failed to create paper for file %s in submission %s: %s",
                        file_row.get("id"),
                        submission_id,
                        exc,
                    )
                    filename = file_row.get("original_filename") or file_row.get("id")
                    err_msg = str(exc).strip()
                    if "duplicate key" in err_msg.lower() or "unique constraint" in err_msg.lower():
                        clean_reason = "A paper with this title, subject, year, and exam type already exists."
                    else:
                        clean_reason = err_msg.split("\n")[0]
                    raise DatabaseError(
                        f"Failed to publish paper '{filename}': {clean_reason}"
                    ) from exc

        # Resolve thank-you message
        thank_you = (req.thank_you_message or "").strip() or DEFAULT_THANK_YOU_MESSAGE

        # Mark submission as approved
        self._repo.update_status(
            submission_id=submission_id,
            status="approved",
            thank_you_message=thank_you,
        )

        logger.info(
            "Submission %s approved — created paper ids: %s",
            submission_id,
            paper_ids,
        )
        return {
            "submission_id": submission_id,
            "status": "approved",
            "paper_ids": paper_ids,
            "thank_you_message": thank_you,
        }

    # ------------------------------------------------------------------ #
    # ADMIN: Reject a submission
    # POST /api/v1/submissions/{id}/reject
    # ------------------------------------------------------------------ #


    def reject_submission(
        self,
        submission_id: str,
        req: RejectRequest,
    ) -> dict[str, Any]:
        """
        Reject a pending submission:
          1. Load submission — raise 404 if not found
          2. Verify status == 'pending'
          3. Update status → 'rejected', store optional rejection_reason

        No paper record is created.
        The uploaded files remain in storage for admin reference.
        """
        logger.info(
            "SubmissionsService.reject_submission(submission_id=%s)", submission_id
        )

        sub = self._repo.get_by_id(submission_id)
        if sub is None:
            raise NotFoundError(resource="Submission", identifier=submission_id)

        if sub["status"] != "pending":
            raise ValidationError(
                f"Submission is already '{sub['status']}' — only pending submissions can be rejected."
            )

        self._repo.update_status(
            submission_id,
            status="rejected",
            rejection_reason=req.rejection_reason,
        )

        logger.info("Submission %s rejected", submission_id)
        return {
            "submission_id": submission_id,
            "status": "rejected",
            "rejection_reason": req.rejection_reason,
        }

    # ------------------------------------------------------------------ #
    # ADMIN: Restore a rejected submission to pending
    # POST /api/v1/submissions/{id}/restore
    # ------------------------------------------------------------------ #

    def restore_submission(
        self,
        submission_id: str,
    ) -> dict[str, Any]:
        """
        Restore a rejected submission back to pending so it can be
        reviewed again:
          1. Load submission — raise 404 if not found
          2. Verify status == 'rejected' (only rejected can be restored)
          3. Clear rejection_reason and reviewed_at, set status → 'pending'

        Returns a dict with the new status.
        Raises ValidationError if submission is not rejected.
        """
        logger.info(
            "SubmissionsService.restore_submission(submission_id=%s)", submission_id
        )

        sub = self._repo.get_by_id(submission_id)
        if sub is None:
            raise NotFoundError(resource="Submission", identifier=submission_id)

        if sub["status"] != "rejected":
            raise ValidationError(
                f"Submission is '{sub['status']}' — only rejected submissions can be restored to pending."
            )

        self._repo.restore_to_pending(submission_id)

        logger.info("Submission %s restored to pending", submission_id)
        return {
            "submission_id": submission_id,
            "status": "pending",
        }

    # ------------------------------------------------------------------ #
    # ADMIN: Secure file download (proxy)
    # GET /api/v1/submissions/files/{file_id}/download
    # ------------------------------------------------------------------ #

    def download_file(
        self,
        file_id: str,
    ) -> tuple[bytes, str, str]:
        """
        Securely download a submission file for the admin.

        Verifies the file exists (implicitly verifying it belongs to
        a real submission), then streams the bytes from the private
        Supabase bucket.

        Args:
            file_id: UUID of the submission_files row.

        Returns:
            Tuple of (file_bytes, content_type, original_filename).

        Raises:
            NotFoundError if the file_id does not exist.
            DatabaseError if the storage download fails.
        """
        logger.info(
            "SubmissionsService.download_file(file_id=%s)", file_id
        )

        file_row = self._repo.get_file_by_id(file_id)
        if file_row is None:
            raise NotFoundError(resource="SubmissionFile", identifier=file_id)

        storage_path = file_row["storage_path"]
        original_filename = file_row["original_filename"]
        ext = file_row.get("file_type", "").lower()
        content_type = _EXT_TO_MIME.get(ext, "application/octet-stream")

        try:
            file_bytes = self._repo.download_file_bytes(storage_path)
        except RuntimeError as exc:
            raise DatabaseError(
                "Failed to retrieve the file from storage. Please try again."
            ) from exc

        return file_bytes, content_type, original_filename

    # ------------------------------------------------------------------ #
    # USER: Get authenticated user's own submissions
    # GET /api/v1/submissions/my
    # ------------------------------------------------------------------ #

    def get_user_submissions(
        self, firebase_uid: str, email: str | None = None
    ) -> UserSubmissionsResponse:
        """
        Return all submissions made by the current authenticated user.
        Includes attached files and linked published papers if approved.
        """
        logger.info(
            "SubmissionsService.get_user_submissions(firebase_uid=%s)", firebase_uid
        )
        rows = self._repo.get_user_submissions(firebase_uid=firebase_uid, email=email)

        items = []
        for r in rows:
            files = [
                UserSubmissionFile(
                    id=f["id"],
                    original_filename=f.get("original_filename") or "paper.pdf",
                    file_type=f.get("file_type") or "pdf",
                    file_size=f.get("file_size") or 0,
                    created_at=f["created_at"],
                )
                for f in r.get("files", [])
            ]
            published = [
                UserSubmissionPaper(
                    id=p["id"],
                    title=p["title"],
                    subject_name=p.get("subject_name"),
                    class_name=p.get("class_name"),
                    exam_type=p.get("exam_type"),
                    year=p.get("year"),
                    paper_type=p.get("paper_type"),
                    public_url=p.get("public_url"),
                )
                for p in r.get("published_papers", [])
            ]
            items.append(
                UserSubmissionItem(
                    id=r["id"],
                    publisher_name=r["publisher_name"],
                    details=r.get("details"),
                    status=r["status"],
                    rejection_reason=r.get("rejection_reason"),
                    thank_you_message=r.get("thank_you_message"),
                    reviewed_at=r.get("reviewed_at"),
                    created_at=r["created_at"],
                    files=files,
                    published_papers=published,
                )
            )

        return UserSubmissionsResponse(data=items, total=len(items))


    def get_user_stats(
        self, firebase_uid: str, email: str | None = None
    ) -> dict[str, int]:
        """Fetch submission statistics for user profile."""
        return self._repo.get_user_submission_stats(firebase_uid=firebase_uid, email=email)

    # ------------------------------------------------------------------ #
    # ADMIN: Delete a submission
    # DELETE /api/v1/submissions/{id}
    # ------------------------------------------------------------------ #

    def delete_submission(
        self, submission_id: str, current_user: dict | None = None
    ) -> SubmissionDeleteResponse:
        """
        Permanently delete a submission (pending, rejected, or approved):
          1. Load submission — raise 404 if not found
          2. Delete attached private files from Supabase Storage, delete any linked published
             papers from public storage and PostgreSQL, and delete submission records.
          3. Record deletion in audit log.

        Returns a SubmissionDeleteResponse.
        """
        logger.info(
            "SubmissionsService.delete_submission(submission_id=%s)", submission_id
        )

        sub = self._repo.get_by_id(submission_id)
        if sub is None:
            raise NotFoundError(resource="Submission", identifier=submission_id)

        admin_id = current_user.get("firebase_uid") or current_user.get("id") if current_user else None
        admin_email = current_user.get("email") if current_user else None

        deleted_paper_ids = self._repo.delete_submission(
            submission_id, admin_id=admin_id, admin_email=admin_email
        )

        logger.info(
            "Submission %s deleted successfully (linked papers: %s)",
            submission_id,
            deleted_paper_ids,
        )
        return SubmissionDeleteResponse(
            submission_id=submission_id,
            deleted=True,
            deleted_paper_ids=deleted_paper_ids,
            message="Submission and associated published papers deleted successfully.",
        )


