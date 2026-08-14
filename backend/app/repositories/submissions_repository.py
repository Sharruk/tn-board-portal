"""
Submissions repository — all Supabase data access for the
`submissions` and `submission_files` tables.

This is the ONLY layer that calls Supabase for submissions.
Services call these methods; routes never touch Supabase directly.

Uses the SERVICE ROLE client (bypasses RLS) for all operations so
that the backend can read and modify submissions regardless of the
calling user's auth state.  Auth checking is handled at the service
and route level, not here.

File upload uses the Supabase Storage Python client with the service
role key so that files are stored server-side — never exposing the
service role key to the public browser.
"""

import logging
import uuid
from typing import Any

from supabase import Client

logger = logging.getLogger(__name__)

# Allowed file extensions and MIME types
ALLOWED_EXTENSIONS: set[str] = {"pdf", "doc", "docx", "jpg", "jpeg", "png"}
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}

# Limits
MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
MAX_FILES_PER_SUBMISSION: int = 5

# Storage bucket name
SUBMISSIONS_BUCKET: str = "submissions"


class SubmissionsRepository:
    """Data access layer for the submissions and submission_files tables."""

    def __init__(self, db: Client) -> None:
        """
        Args:
            db: Supabase client.  Should be the SERVICE ROLE client for
                all admin operations and file uploads.  The public POST
                endpoint uses the anon client (limited to INSERT only).
        """
        self._db = db

    # ------------------------------------------------------------------ #
    # Create submission (public endpoint)
    # ------------------------------------------------------------------ #

    def create_submission(
        self,
        publisher_name: str,
        email: str,
        firebase_uid: str,
        details: str | None,
    ) -> dict[str, Any]:
        """
        Insert a new submission row with status = 'pending'.

        Returns the created row dict including the generated UUID.
        """
        logger.debug(
            "SubmissionsRepository.create_submission(email=%s, firebase_uid=%s)", email, firebase_uid
        )
        response = (
            self._db.table("submissions")
            .insert(
                {
                    "publisher_name": publisher_name,
                    "email": email,
                    "firebase_uid": firebase_uid,
                    "details": details,
                    "status": "pending",
                }
            )
            .execute()
        )
        if not response.data:
            raise RuntimeError("Failed to create submission — no data returned")
        return response.data[0]

    # ------------------------------------------------------------------ #
    # Upload file to storage + insert submission_files row
    # ------------------------------------------------------------------ #

    def upload_file(
        self,
        submission_id: str,
        filename: str,
        content: bytes,
        content_type: str,
        file_size: int,
        ext: str,
    ) -> dict[str, Any]:
        """
        Upload one file to Supabase Storage and insert a submission_files row.

        Storage path: submissions/{submission_id}/{random_uuid}.{ext}
        The original filename is preserved for display only — never used as key.

        Args:
            submission_id: UUID of the parent submission.
            filename:      Original filename (for display/storage in DB).
            content:       Raw file bytes.
            content_type:  MIME type of the file.
            file_size:     Size in bytes.
            ext:           Lowercase file extension (without dot).

        Returns:
            The inserted submission_files row dict.
        """
        safe_name = f"{uuid.uuid4()}.{ext}"
        storage_path = f"{submission_id}/{safe_name}"

        logger.debug(
            "SubmissionsRepository.upload_file(submission_id=%s, path=%s)",
            submission_id,
            storage_path,
        )

        # Upload to Supabase Storage
        self._db.storage.from_(SUBMISSIONS_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "false"},
        )

        # Insert the file metadata row (public_url is not generated for pending files)
        row_response = (
            self._db.table("submission_files")
            .insert(
                {
                    "submission_id": submission_id,
                    "original_filename": filename,
                    "storage_path": storage_path,
                    "file_type": ext,
                    "file_size": file_size,
                }
            )
            .execute()
        )
        if not row_response.data:
            raise RuntimeError(
                f"Failed to insert submission_files row for {storage_path}"
            )
        return row_response.data[0]

    # ------------------------------------------------------------------ #
    # List submissions (admin)
    # ------------------------------------------------------------------ #

    def list_submissions(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Return submissions ordered by created_at DESC.

        Args:
            status: Optional filter ('pending' | 'approved' | 'rejected').
            limit:  Max rows to return.

        Returns:
            List of submission rows.  file_count is fetched separately
            and merged in the service layer.
        """
        logger.debug(
            "SubmissionsRepository.list_submissions(status=%s, limit=%s)",
            status,
            limit,
        )
        query = (
            self._db.table("submissions")
            .select("id,publisher_name,email,firebase_uid,details,status,rejection_reason,reviewed_at,created_at")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if status:
            query = query.eq("status", status)

        response = query.execute()
        return response.data or []

    def count_files_for_submissions(
        self, submission_ids: list[str]
    ) -> dict[str, int]:
        """
        Return {submission_id: file_count} for a list of submission IDs.
        Used by the service layer to enrich list responses.
        """
        if not submission_ids:
            return {}

        response = (
            self._db.table("submission_files")
            .select("submission_id")
            .in_("submission_id", submission_ids)
            .execute()
        )
        counts: dict[str, int] = {}
        for row in (response.data or []):
            sid = row["submission_id"]
            counts[sid] = counts.get(sid, 0) + 1
        return counts

    # ------------------------------------------------------------------ #
    # Get single submission (admin)
    # ------------------------------------------------------------------ #

    def get_by_id(self, submission_id: str) -> dict[str, Any] | None:
        """
        Return one submission row, or None if not found.
        """
        logger.debug(
            "SubmissionsRepository.get_by_id(submission_id=%s)", submission_id
        )
        response = (
            self._db.table("submissions")
            .select("id,publisher_name,email,firebase_uid,details,status,rejection_reason,reviewed_at,created_at")
            .eq("id", submission_id)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]

    def get_file_by_id(self, file_id: str) -> dict[str, Any] | None:
        """
        Return one submission_files row by its primary key, or None if not found.
        Used by the download endpoint to verify the file exists and get its path.
        """
        logger.debug(
            "SubmissionsRepository.get_file_by_id(file_id=%s)", file_id
        )
        response = (
            self._db.table("submission_files")
            .select(
                "id,submission_id,original_filename,storage_path,"
                "file_type,file_size,created_at"
            )
            .eq("id", file_id)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]

    def download_file_bytes(self, storage_path: str) -> bytes:
        """
        Download a file from the private submissions bucket using the
        service-role client and return the raw bytes.

        Args:
            storage_path: The storage object key (e.g. ``{sub_id}/{uuid}.pdf``).

        Returns:
            Raw file bytes.

        Raises:
            RuntimeError if the download fails.
        """
        logger.debug(
            "SubmissionsRepository.download_file_bytes(path=%s)", storage_path
        )
        try:
            data = self._db.storage.from_(SUBMISSIONS_BUCKET).download(storage_path)
        except Exception as exc:
            logger.error(
                "Failed to download file from storage path %s: %s",
                storage_path,
                exc,
            )
            raise RuntimeError(f"Storage download failed: {exc}") from exc
        return data

    def restore_to_pending(
        self, submission_id: str
    ) -> dict[str, Any]:
        """
        Reset a rejected submission back to 'pending', clearing
        rejection_reason and reviewed_at so it can be reviewed again.

        Returns the updated row.
        """
        logger.debug(
            "SubmissionsRepository.restore_to_pending(submission_id=%s)",
            submission_id,
        )
        response = (
            self._db.table("submissions")
            .update(
                {
                    "status": "pending",
                    "rejection_reason": None,
                    "reviewed_at": None,
                }
            )
            .eq("id", submission_id)
            .execute()
        )
        if not response.data:
            raise RuntimeError(
                f"Failed to restore submission {submission_id} — no data returned"
            )
        return response.data[0]

    def get_files(self, submission_id: str) -> list[dict[str, Any]]:
        """
        Return all submission_files rows for a given submission.
        Generates short-lived signed URLs for admin viewing.
        """
        logger.debug(
            "SubmissionsRepository.get_files(submission_id=%s)", submission_id
        )
        response = (
            self._db.table("submission_files")
            .select(
                "id,submission_id,original_filename,storage_path,public_url,"
                "file_type,file_size,created_at"
            )
            .eq("submission_id", submission_id)
            .order("created_at")
            .execute()
        )
        
        files = response.data or []
        for file_row in files:
            # Generate a 1-hour signed URL for secure viewing
            try:
                signed_url_response = self._db.storage.from_(SUBMISSIONS_BUCKET).create_signed_url(
                    file_row["storage_path"], 3600
                )
                if signed_url_response and "signedURL" in signed_url_response:
                    file_row["signed_url"] = signed_url_response["signedURL"]
            except Exception as e:
                logger.error("Failed to generate signed URL for %s: %s", file_row["storage_path"], e)
                file_row["signed_url"] = None

        return files

    # ------------------------------------------------------------------ #
    # Update submission status (admin)
    # ------------------------------------------------------------------ #

    def update_status(
        self,
        submission_id: str,
        status: str,
        rejection_reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Update the status + reviewed_at of a submission.
        Optionally sets rejection_reason for rejected submissions.

        Returns the updated row.
        """
        logger.debug(
            "SubmissionsRepository.update_status(submission_id=%s, status=%s)",
            submission_id,
            status,
        )
        from datetime import datetime, timezone

        payload: dict[str, Any] = {
            "status": status,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        if rejection_reason is not None:
            payload["rejection_reason"] = rejection_reason

        response = (
            self._db.table("submissions")
            .update(payload)
            .eq("id", submission_id)
            .execute()
        )
        if not response.data:
            raise RuntimeError(
                f"Failed to update submission {submission_id} — no data returned"
            )
        return response.data[0]

    # ------------------------------------------------------------------ #
    # Create paper from approved submission (admin)
    # ------------------------------------------------------------------ #

    def create_paper_from_file(
        self,
        file_row: dict[str, Any],
        subject_id: int,
        exam_type: str,
        year: int,
        paper_type: str,
        month: str | None,
        district: str | None,
        submission: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Insert one paper row derived from an approved submission file.
        Copies the file from the private submissions bucket to the public papers bucket.

        The title is built from the original filename or submission details.
        is_visible is set to True so the paper is immediately public.

        Returns the inserted papers row.
        """
        # Copy the file to the public papers bucket
        original_path = file_row.get("storage_path")
        ext = file_row.get("file_type")
        new_path = f"{uuid.uuid4()}.{ext}"

        logger.debug(
            "SubmissionsRepository.create_paper_from_file: Copying file from %s to papers/%s",
            original_path,
            new_path,
        )

        try:
            # Download from submissions and upload to papers, or use copy/move.
            # Supabase Python client doesn't have cross-bucket copy, so we download then upload
            file_data = self._db.storage.from_(SUBMISSIONS_BUCKET).download(original_path)
            # Mime type guessing based on extension
            content_type = "application/octet-stream"
            if ext == "pdf": content_type = "application/pdf"
            elif ext in ["jpg", "jpeg"]: content_type = "image/jpeg"
            elif ext == "png": content_type = "image/png"
            elif ext in ["doc", "docx"]: content_type = "application/msword"
            
            self._db.storage.from_("papers").upload(
                path=new_path,
                file=file_data,
                file_options={"content-type": content_type, "upsert": "false"},
            )
        except Exception as e:
            logger.error("Failed to copy file to papers bucket: %s", e)
            raise RuntimeError(f"Failed to copy file to public bucket: {e}")

        # Get the new public URL from papers bucket
        url_response = self._db.storage.from_("papers").get_public_url(new_path)
        public_url = url_response if isinstance(url_response, str) else None

        # Build a sensible title
        raw_name = file_row.get("original_filename", "")
        # Strip extension for title
        base_name = raw_name.rsplit(".", 1)[0] if "." in raw_name else raw_name
        title = base_name.replace("_", " ").replace("-", " ").strip()
        if not title:
            title = submission.get("details") or f"Submitted Paper {submission['id'][:8]}"

        logger.debug(
            "SubmissionsRepository.create_paper_from_file(title=%r, subject_id=%s)",
            title,
            subject_id,
        )

        response = (
            self._db.table("papers")
            .insert(
                {
                    "subject_id": subject_id,
                    "exam_type": exam_type,
                    "year": year,
                    "title": title,
                    "paper_type": paper_type,
                    "month": month,
                    "district": district,
                    "file_path": new_path,
                    "public_url": public_url,
                    "original_filename": file_row.get("original_filename"),
                    "is_visible": True,
                    "download_count": 0,
                }
            )
            .execute()
        )
        if not response.data:
            raise RuntimeError("Failed to create paper from submission file")
        return response.data[0]
