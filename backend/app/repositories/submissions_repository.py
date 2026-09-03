"""
Submissions repository — direct PostgreSQL data access for `submissions` and `submission_files` tables,
with Supabase Storage client integration for file binary operations.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.db.storage import get_storage_client

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
    """Data access layer for the submissions domain."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._db = db
        self._storage = storage if storage is not None else get_storage_client()

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
        """
        logger.debug(
            "SubmissionsRepository.create_submission(email=%s, firebase_uid=%s)", email, firebase_uid
        )
        stmt = text(
            """
            INSERT INTO submissions (publisher_name, email, firebase_uid, details, status)
            VALUES (:publisher_name, :email, :firebase_uid, :details, 'pending')
            RETURNING id, publisher_name, email, firebase_uid, details, status, created_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "publisher_name": publisher_name,
                "email": email,
                "firebase_uid": firebase_uid,
                "details": details,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to create submission — no data returned")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

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
        """
        safe_name = f"{uuid.uuid4()}.{ext}"
        storage_path = f"{submission_id}/{safe_name}"

        logger.debug(
            "SubmissionsRepository.upload_file(submission_id=%s, path=%s)",
            submission_id,
            storage_path,
        )

        # Upload to Supabase Storage
        self._storage.from_(SUBMISSIONS_BUCKET).upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "false"},
        )

        # Insert metadata row in PostgreSQL
        stmt = text(
            """
            INSERT INTO submission_files (submission_id, original_filename, storage_path, file_type, file_size)
            VALUES (:submission_id, :original_filename, :storage_path, :file_type, :file_size)
            RETURNING id, submission_id, original_filename, storage_path, file_type, file_size, created_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "submission_id": submission_id,
                "original_filename": filename,
                "storage_path": storage_path,
                "file_type": ext,
                "file_size": file_size,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError(f"Failed to insert submission_files row for {storage_path}")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d["submission_id"] = str(d["submission_id"])
        return d

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
        """
        logger.debug(
            "SubmissionsRepository.list_submissions(status=%s, limit=%s)",
            status,
            limit,
        )
        sql = """
            SELECT id, publisher_name, email, firebase_uid, details, status, rejection_reason, thank_you_message, reviewed_at, created_at
            FROM submissions
        """
        params: dict[str, Any] = {"limit": limit}
        if status:
            sql += " WHERE status = :status"
            params["status"] = status

        sql += " ORDER BY created_at DESC LIMIT :limit"

        try:
            stmt = text(sql)
            result = self._db.execute(stmt, params)
            rows = []
            for r in result.fetchall():
                d = dict(r._mapping)
                d["id"] = str(d["id"])
                rows.append(d)
            return rows
        except Exception as exc:
            err_msg = str(exc).lower()
            if "thank_you_message" in err_msg or "undefinedcolumn" in err_msg or "no such column" in err_msg:
                self._db.rollback()
                fallback_sql = """
                    SELECT id, publisher_name, email, firebase_uid, details, status, rejection_reason, reviewed_at, created_at
                    FROM submissions
                """
                if status:
                    fallback_sql += " WHERE status = :status"
                fallback_sql += " ORDER BY created_at DESC LIMIT :limit"
                result = self._db.execute(text(fallback_sql), params)
                rows = []
                for r in result.fetchall():
                    d = dict(r._mapping)
                    d["id"] = str(d["id"])
                    d.setdefault("thank_you_message", None)
                    rows.append(d)
                return rows
            raise

    def count_files_for_submissions(
        self, submission_ids: list[str]
    ) -> dict[str, int]:
        """
        Return {submission_id: file_count} for a list of submission IDs.
        """
        if not submission_ids:
            return {}

        stmt = text(
            """
            SELECT submission_id::text, COUNT(*)::int AS file_count
            FROM submission_files
            WHERE submission_id::text IN :submission_ids
            GROUP BY submission_id
            """
        ).bindparams(bindparam("submission_ids", expanding=True))

        result = self._db.execute(stmt, {"submission_ids": list(submission_ids)})
        counts: dict[str, int] = {}
        for r in result.fetchall():
            counts[r[0]] = r[1]
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
        stmt = text(
            """
            SELECT id, publisher_name, email, firebase_uid, details, status, rejection_reason, thank_you_message, reviewed_at, created_at
            FROM submissions
            WHERE id::text = :submission_id
            """
        )
        try:
            result = self._db.execute(stmt, {"submission_id": submission_id})
            row = result.fetchone()
        except Exception as exc:
            err_msg = str(exc).lower()
            if "thank_you_message" in err_msg or "undefinedcolumn" in err_msg or "no such column" in err_msg:
                self._db.rollback()
                fallback_stmt = text(
                    """
                    SELECT id, publisher_name, email, firebase_uid, details, status, rejection_reason, reviewed_at, created_at
                    FROM submissions
                    WHERE id::text = :submission_id
                    """
                )
                result = self._db.execute(fallback_stmt, {"submission_id": submission_id})
                row = result.fetchone()
            else:
                raise
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d.setdefault("thank_you_message", None)
        return d

    def get_file_by_id(self, file_id: str) -> dict[str, Any] | None:
        """
        Return one submission_files row by its primary key, or None if not found.
        """
        logger.debug(
            "SubmissionsRepository.get_file_by_id(file_id=%s)", file_id
        )
        stmt = text(
            """
            SELECT id, submission_id, original_filename, storage_path, file_type, file_size, created_at
            FROM submission_files
            WHERE id::text = :file_id
            """
        )
        result = self._db.execute(stmt, {"file_id": file_id})
        row = result.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d["submission_id"] = str(d["submission_id"])
        return d

    def download_file_bytes(self, storage_path: str) -> bytes:
        """
        Download a file from the private submissions bucket.
        """
        logger.debug(
            "SubmissionsRepository.download_file_bytes(path=%s)", storage_path
        )
        try:
            data = self._storage.from_(SUBMISSIONS_BUCKET).download(storage_path)
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
        Reset a rejected submission back to 'pending'.
        """
        logger.debug(
            "SubmissionsRepository.restore_to_pending(submission_id=%s)",
            submission_id,
        )
        stmt = text(
            """
            UPDATE submissions
            SET status = 'pending', rejection_reason = NULL, thank_you_message = NULL, reviewed_at = NULL
            WHERE id::text = :submission_id
            RETURNING id, publisher_name, email, firebase_uid, details, status, rejection_reason, thank_you_message, reviewed_at, created_at
            """
        )
        try:
            result = self._db.execute(stmt, {"submission_id": submission_id})
            self._db.commit()
            row = result.fetchone()
        except Exception as exc:
            err_msg = str(exc).lower()
            if "thank_you_message" in err_msg or "undefinedcolumn" in err_msg or "no such column" in err_msg:
                self._db.rollback()
                fallback_stmt = text(
                    """
                    UPDATE submissions
                    SET status = 'pending', rejection_reason = NULL, reviewed_at = NULL
                    WHERE id::text = :submission_id
                    RETURNING id, publisher_name, email, firebase_uid, details, status, rejection_reason, reviewed_at, created_at
                    """
                )
                result = self._db.execute(fallback_stmt, {"submission_id": submission_id})
                self._db.commit()
                row = result.fetchone()
            else:
                raise
        if not row:
            raise RuntimeError(f"Failed to restore submission {submission_id} — no data returned")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d.setdefault("thank_you_message", None)
        return d

    def get_files(self, submission_id: str) -> list[dict[str, Any]]:
        """
        Return all submission_files rows for a given submission with signed URLs.
        """
        logger.debug(
            "SubmissionsRepository.get_files(submission_id=%s)", submission_id
        )
        stmt = text(
            """
            SELECT id, submission_id, original_filename, storage_path, public_url, file_type, file_size, created_at
            FROM submission_files
            WHERE submission_id::text = :submission_id
            ORDER BY created_at
            """
        )
        result = self._db.execute(stmt, {"submission_id": submission_id})
        files = []
        for r in result.fetchall():
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            d["submission_id"] = str(d["submission_id"])
            files.append(d)

        for file_row in files:
            try:
                signed_url_response = self._storage.from_(SUBMISSIONS_BUCKET).create_signed_url(
                    file_row["storage_path"], 3600
                )
                if signed_url_response and "signedURL" in signed_url_response:
                    file_row["signed_url"] = signed_url_response["signedURL"]
                elif isinstance(signed_url_response, dict) and "signedUrl" in signed_url_response:
                    file_row["signed_url"] = signed_url_response["signedUrl"]
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
        thank_you_message: str | None = None,
    ) -> dict[str, Any]:
        """
        Update the status + reviewed_at of a submission.
        """
        logger.debug(
            "SubmissionsRepository.update_status(submission_id=%s, status=%s)",
            submission_id,
            status,
        )
        now = datetime.now(timezone.utc)
        stmt = text(
            """
            UPDATE submissions
            SET status = :status, reviewed_at = :reviewed_at, rejection_reason = :rejection_reason, thank_you_message = :thank_you_message
            WHERE id::text = :submission_id
            RETURNING id, publisher_name, email, firebase_uid, details, status, rejection_reason, thank_you_message, reviewed_at, created_at
            """
        )
        try:
            result = self._db.execute(
                stmt,
                {
                    "submission_id": submission_id,
                    "status": status,
                    "reviewed_at": now,
                    "rejection_reason": rejection_reason,
                    "thank_you_message": thank_you_message,
                },
            )
            self._db.commit()
            row = result.fetchone()
        except Exception as exc:
            err_msg = str(exc).lower()
            if "thank_you_message" in err_msg or "undefinedcolumn" in err_msg or "no such column" in err_msg:
                self._db.rollback()
                fallback_stmt = text(
                    """
                    UPDATE submissions
                    SET status = :status, reviewed_at = :reviewed_at, rejection_reason = :rejection_reason
                    WHERE id::text = :submission_id
                    RETURNING id, publisher_name, email, firebase_uid, details, status, rejection_reason, reviewed_at, created_at
                    """
                )
                result = self._db.execute(
                    fallback_stmt,
                    {
                        "submission_id": submission_id,
                        "status": status,
                        "reviewed_at": now,
                        "rejection_reason": rejection_reason,
                    },
                )
                self._db.commit()
                row = result.fetchone()
            else:
                raise
        if not row:
            raise RuntimeError(f"Failed to update submission {submission_id} — no data returned")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d.setdefault("thank_you_message", thank_you_message)
        return d


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
        title: str | None = None,
        download_filename: str | None = None,
        description: str | None = None,
        youtube_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Insert one paper row derived from an approved submission file.
        Copies the file from private submissions bucket to public papers bucket.
        """
        original_path = file_row.get("storage_path")
        if not original_path:
            raise ValueError(f"Submission file {file_row.get('id')} has no storage path.")

        ext = file_row.get("file_type") or "pdf"
        ext = ext.lstrip(".").lower()
        new_path = f"{uuid.uuid4()}.{ext}"

        logger.debug(
            "SubmissionsRepository.create_paper_from_file: Copying file from %s to papers/%s",
            original_path,
            new_path,
        )

        try:
            file_data = self._storage.from_(SUBMISSIONS_BUCKET).download(original_path)
        except Exception as e:
            logger.error("Failed to download file from submissions bucket (%s): %s", original_path, e)
            raise RuntimeError(f"Storage download failed for '{original_path}': {e}") from e

        content_type = "application/octet-stream"
        if ext == "pdf":
            content_type = "application/pdf"
        elif ext in ["jpg", "jpeg"]:
            content_type = "image/jpeg"
        elif ext == "png":
            content_type = "image/png"
        elif ext in ["doc", "docx"]:
            content_type = "application/msword"

        try:
            self._storage.from_("papers").upload(
                path=new_path,
                file=file_data,
                file_options={"content-type": content_type, "upsert": "false"},
            )
        except Exception as e:
            logger.error("Failed to upload file to papers bucket (%s): %s", new_path, e)
            raise RuntimeError(f"Public storage upload failed for '{new_path}': {e}") from e

        url_response = self._storage.from_("papers").get_public_url(new_path)
        if isinstance(url_response, str):
            public_url = url_response
        elif isinstance(url_response, dict):
            public_url = url_response.get("publicUrl") or url_response.get("publicURL")
        else:
            public_url = None

        raw_name = file_row.get("original_filename", "")
        base_name = raw_name.rsplit(".", 1)[0] if "." in raw_name else raw_name

        # If admin entered a custom title, use it; otherwise compute canonical title
        final_title = (title or "").strip()
        if not final_title:
            class_name = ""
            subject_name = ""
            try:
                subj_stmt = text(
                    """
                    SELECT s.name AS subject_name, c.name AS class_name
                    FROM subjects s
                    JOIN classes c ON s.class_id = c.id
                    WHERE s.id = :subject_id
                    """
                )
                subj_row = self._db.execute(subj_stmt, {"subject_id": subject_id}).fetchone()
                if subj_row:
                    mapping = dict(subj_row._mapping)
                    class_name = mapping.get("class_name") or ""
                    subject_name = mapping.get("subject_name") or ""
            except Exception as e:
                logger.warning("Failed to lookup subject/class for canonical title: %s", e)

            type_str = "Question Paper" if paper_type == "question" else "Answer Key"
            title_parts = [
                class_name,
                subject_name,
                exam_type,
                month or "",
                str(year) if year else "",
                district or "",
                type_str,
            ]
            final_title = " ".join(p for p in title_parts if p).strip()
            if not final_title:
                final_title = base_name.replace("_", " ").replace("-", " ").strip()
            if not final_title:
                final_title = submission.get("details") or f"Submitted Paper {str(submission['id'])[:8]}"

        # Prevent duplicate title collisions
        try:
            chk_stmt = text(
                """
                SELECT id FROM papers
                WHERE subject_id = :subject_id AND title = :title AND year = :year AND exam_type = :exam_type
                """
            )
            existing = self._db.execute(
                chk_stmt,
                {"subject_id": subject_id, "title": final_title, "year": year, "exam_type": exam_type},
            ).fetchall()
            if existing:
                final_title = f"{final_title} ({str(submission['id'])[:6]})"
        except Exception as e:
            logger.warning("Uniqueness check for paper title query failed: %s", e)

        # Resolve approved download filename
        clean_dl = (download_filename or "").strip()
        if clean_dl:
            if not clean_dl.lower().endswith(f".{ext}"):
                clean_dl = f"{clean_dl}.{ext}"
            final_download_filename = clean_dl
        else:
            final_download_filename = file_row.get("original_filename") or raw_name or f"{final_title}.{ext}"

        final_description = (description or "").strip() or None
        submission_id = str(submission["id"]) if submission.get("id") else None
        contributor_name = submission.get("publisher_name")

        params = {
            "subject_id": subject_id,
            "exam_type": exam_type,
            "year": year,
            "title": final_title,
            "description": final_description,
            "paper_type": paper_type,
            "month": month,
            "district": district,
            "file_path": new_path,
            "public_url": public_url,
            "youtube_url": (youtube_url.strip() if youtube_url else None),
            "original_filename": final_download_filename,
            "submission_id": submission_id,
            "contributor_name": contributor_name,
        }

        # Attempt primary insert with description, status, submission_id, contributor_name
        stmt_full = text(
            """
            INSERT INTO papers (
                subject_id, exam_type, year, title, description, paper_type,
                month, district, file_path, public_url, youtube_url, original_filename,
                is_visible, download_count, status, submission_id, contributor_name
            )
            VALUES (
                :subject_id, :exam_type, :year, :title, :description, :paper_type,
                :month, :district, :file_path, :public_url, :youtube_url, :original_filename,
                true, 0, 'published', :submission_id, :contributor_name
            )
            RETURNING id, subject_id, exam_type, year, title, description, paper_type, month, district, file_path, public_url, youtube_url, original_filename, is_visible, download_count, status, submission_id, contributor_name, created_at
            """
        )

        try:
            result = self._db.execute(stmt_full, params)
            self._db.commit()
            row = result.fetchone()
            if not row:
                raise RuntimeError("Failed to create paper from submission file — no data returned")
            d = dict(row._mapping)
            if d.get("submission_id"):
                d["submission_id"] = str(d["submission_id"])
            return d
        except Exception as e:
            self._db.rollback()
            err_msg = str(e).lower()
            if "does not exist" not in err_msg and "undefinedcolumn" not in err_msg:
                logger.error("Failed to insert paper record: %s", e)
                raise

            logger.warning("Primary paper INSERT failed (%s), trying resilient column fallback...", e)

            # Fallback 1: without 'status' column if undefined column error
            if "status" in err_msg:
                try:
                    stmt_no_status = text(
                        """
                        INSERT INTO papers (
                            subject_id, exam_type, year, title, description, paper_type,
                            month, district, file_path, public_url, youtube_url, original_filename,
                            is_visible, download_count, submission_id, contributor_name
                        )
                        VALUES (
                            :subject_id, :exam_type, :year, :title, :description, :paper_type,
                            :month, :district, :file_path, :public_url, :youtube_url, :original_filename,
                            true, 0, :submission_id, :contributor_name
                        )
                        RETURNING id, subject_id, exam_type, year, title, description, paper_type, month, district, file_path, public_url, youtube_url, original_filename, is_visible, download_count, submission_id, contributor_name, created_at
                        """
                    )
                    result = self._db.execute(stmt_no_status, params)
                    self._db.commit()
                    row = result.fetchone()
                    if row:
                        d = dict(row._mapping)
                        d.setdefault("status", "published")
                        if d.get("submission_id"):
                            d["submission_id"] = str(d["submission_id"])
                        return d
                except Exception as fb_err:
                    self._db.rollback()
                    logger.warning("Fallback without status failed: %s", fb_err)

            # Fallback 2: without 'description' and 'status' if both are unmigrated
            try:
                stmt_legacy = text(
                    """
                    INSERT INTO papers (
                        subject_id, exam_type, year, title, paper_type,
                        month, district, file_path, public_url, youtube_url, original_filename,
                        is_visible, download_count, submission_id, contributor_name
                    )
                    VALUES (
                        :subject_id, :exam_type, :year, :title, :paper_type,
                        :month, :district, :file_path, :public_url, :youtube_url, :original_filename,
                        true, 0, :submission_id, :contributor_name
                    )
                    RETURNING id, subject_id, exam_type, year, title, paper_type, month, district, file_path, public_url, youtube_url, original_filename, is_visible, download_count, submission_id, contributor_name, created_at
                    """
                )
                result = self._db.execute(stmt_legacy, params)
                self._db.commit()
                row = result.fetchone()
                if row:
                    d = dict(row._mapping)
                    d.setdefault("status", "published")
                    d.setdefault("description", final_description)
                    if d.get("submission_id"):
                        d["submission_id"] = str(d["submission_id"])
                    return d
            except Exception as leg_err:
                self._db.rollback()
                logger.error("All fallback paper INSERTs failed: %s", leg_err)
                raise

    def create_paper_from_prepared_file(
        self,
        file_bytes: bytes,
        subject_id: int,
        exam_type: str,
        year: int,
        paper_type: str,
        month: str | None,
        district: str | None,
        submission: dict[str, Any],
        title: str | None = None,
        download_filename: str | None = None,
        description: str | None = None,
        youtube_url: str | None = None,
        file_type: str = "pdf",
    ) -> dict[str, Any]:
        """
        Insert one paper row derived from an admin-prepared file (e.g. converted PDF).
        Directly uploads the prepared bytes to the public 'papers' storage bucket.
        Preserves original contributor attribution and submission link.
        """
        ext = (file_type or "pdf").lstrip(".").lower()
        new_path = f"{uuid.uuid4()}.{ext}"

        logger.debug(
            "SubmissionsRepository.create_paper_from_prepared_file: Uploading prepared file to papers/%s",
            new_path,
        )

        content_type = "application/pdf"
        if ext in ["jpg", "jpeg"]:
            content_type = "image/jpeg"
        elif ext == "png":
            content_type = "image/png"
        elif ext in ["doc", "docx"]:
            content_type = "application/msword"

        try:
            self._storage.from_("papers").upload(
                path=new_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "false"},
            )
        except Exception as e:
            logger.error("Failed to upload prepared file to papers bucket (%s): %s", new_path, e)
            raise RuntimeError(f"Public storage upload failed for '{new_path}': {e}") from e

        url_response = self._storage.from_("papers").get_public_url(new_path)
        if isinstance(url_response, str):
            public_url = url_response
        elif isinstance(url_response, dict):
            public_url = url_response.get("publicUrl") or url_response.get("publicURL")
        else:
            public_url = None

        # Resolve title
        final_title = (title or "").strip()
        if not final_title:
            class_name = ""
            subject_name = ""
            try:
                subj_stmt = text(
                    """
                    SELECT s.name AS subject_name, c.name AS class_name
                    FROM subjects s
                    JOIN classes c ON s.class_id = c.id
                    WHERE s.id = :subject_id
                    """
                )
                subj_row = self._db.execute(subj_stmt, {"subject_id": subject_id}).fetchone()
                if subj_row:
                    mapping = dict(subj_row._mapping)
                    class_name = mapping.get("class_name") or ""
                    subject_name = mapping.get("subject_name") or ""
            except Exception as e:
                logger.warning("Failed to lookup subject/class for canonical title: %s", e)

            type_str = "Question Paper" if paper_type == "question" else "Answer Key"
            title_parts = [
                class_name,
                subject_name,
                exam_type,
                month or "",
                str(year) if year else "",
                district or "",
                type_str,
            ]
            final_title = " ".join(p for p in title_parts if p).strip()
            if not final_title:
                final_title = submission.get("details") or f"Prepared Paper {str(submission['id'])[:8]}"

        # Prevent duplicate title collisions
        try:
            chk_stmt = text(
                """
                SELECT id FROM papers
                WHERE subject_id = :subject_id AND title = :title AND year = :year AND exam_type = :exam_type
                """
            )
            existing = self._db.execute(
                chk_stmt,
                {"subject_id": subject_id, "title": final_title, "year": year, "exam_type": exam_type},
            ).fetchall()
            if existing:
                final_title = f"{final_title} ({str(submission['id'])[:6]})"
        except Exception as e:
            logger.warning("Uniqueness check for paper title query failed: %s", e)

        # Resolve approved download filename
        clean_dl = (download_filename or "").strip()
        if clean_dl:
            if not clean_dl.lower().endswith(f".{ext}"):
                clean_dl = f"{clean_dl}.{ext}"
            final_download_filename = clean_dl
        else:
            final_download_filename = f"{final_title}.{ext}".replace(" ", "_")

        final_description = (description or "").strip() or None
        submission_id = str(submission["id"]) if submission.get("id") else None
        contributor_name = submission.get("publisher_name")

        params = {
            "subject_id": subject_id,
            "exam_type": exam_type,
            "year": year,
            "title": final_title,
            "description": final_description,
            "paper_type": paper_type,
            "month": month,
            "district": district,
            "file_path": new_path,
            "public_url": public_url,
            "youtube_url": (youtube_url.strip() if youtube_url else None),
            "original_filename": final_download_filename,
            "submission_id": submission_id,
            "contributor_name": contributor_name,
        }

        stmt_full = text(
            """
            INSERT INTO papers (
                subject_id, exam_type, year, title, description, paper_type,
                month, district, file_path, public_url, youtube_url, original_filename,
                is_visible, download_count, status, submission_id, contributor_name
            )
            VALUES (
                :subject_id, :exam_type, :year, :title, :description, :paper_type,
                :month, :district, :file_path, :public_url, :youtube_url, :original_filename,
                true, 0, 'published', :submission_id, :contributor_name
            )
            RETURNING id, subject_id, exam_type, year, title, description, paper_type, month, district, file_path, public_url, youtube_url, original_filename, is_visible, download_count, status, submission_id, contributor_name, created_at
            """
        )

        try:
            result = self._db.execute(stmt_full, params)
            self._db.commit()
            row = result.fetchone()
            if not row:
                raise RuntimeError("Failed to create paper from prepared file — no data returned")
            d = dict(row._mapping)
            if d.get("submission_id"):
                d["submission_id"] = str(d["submission_id"])
            return d
        except Exception as e:
            self._db.rollback()
            err_msg = str(e).lower()
            if "does not exist" not in err_msg and "undefinedcolumn" not in err_msg:
                logger.error("Failed to insert prepared paper record: %s", e)
                raise

            logger.warning("Primary paper INSERT failed (%s), trying resilient fallback...", e)
            if "status" in err_msg:
                try:
                    stmt_no_status = text(
                        """
                        INSERT INTO papers (
                            subject_id, exam_type, year, title, description, paper_type,
                            month, district, file_path, public_url, youtube_url, original_filename,
                            is_visible, download_count, submission_id, contributor_name
                        )
                        VALUES (
                            :subject_id, :exam_type, :year, :title, :description, :paper_type,
                            :month, :district, :file_path, :public_url, :youtube_url, :original_filename,
                            true, 0, :submission_id, :contributor_name
                        )
                        RETURNING id, subject_id, exam_type, year, title, description, paper_type, month, district, file_path, public_url, youtube_url, original_filename, is_visible, download_count, submission_id, contributor_name, created_at
                        """
                    )
                    result = self._db.execute(stmt_no_status, params)
                    self._db.commit()
                    row = result.fetchone()
                    if row:
                        d = dict(row._mapping)
                        d.setdefault("status", "published")
                        if d.get("submission_id"):
                            d["submission_id"] = str(d["submission_id"])
                        return d
                except Exception as fb_err:
                    self._db.rollback()
                    logger.warning("Fallback without status failed: %s", fb_err)

            try:
                stmt_legacy = text(
                    """
                    INSERT INTO papers (
                        subject_id, exam_type, year, title, paper_type,
                        month, district, file_path, public_url, youtube_url, original_filename,
                        is_visible, download_count, submission_id, contributor_name
                    )
                    VALUES (
                        :subject_id, :exam_type, :year, :title, :paper_type,
                        :month, :district, :file_path, :public_url, :youtube_url, :original_filename,
                        true, 0, :submission_id, :contributor_name
                    )
                    RETURNING id, subject_id, exam_type, year, title, paper_type, month, district, file_path, public_url, youtube_url, original_filename, is_visible, download_count, submission_id, contributor_name, created_at
                    """
                )
                result = self._db.execute(stmt_legacy, params)
                self._db.commit()
                row = result.fetchone()
                if row:
                    d = dict(row._mapping)
                    d.setdefault("status", "published")
                    d.setdefault("description", final_description)
                    if d.get("submission_id"):
                        d["submission_id"] = str(d["submission_id"])
                    return d
            except Exception as leg_err:
                self._db.rollback()
                logger.error("All fallback paper INSERTs failed: %s", leg_err)
                raise

    # ------------------------------------------------------------------ #
    # User's own submissions & contribution history
    # ------------------------------------------------------------------ #

    def get_user_submissions(
        self, firebase_uid: str, email: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Fetch all submissions created by a specific user with their attached files
        and any linked approved papers.
        """
        logger.debug(
            "SubmissionsRepository.get_user_submissions(firebase_uid=%s, email=%s)",
            firebase_uid,
            email,
        )

        sql = """
            SELECT s.id, s.publisher_name, s.email, s.firebase_uid, s.details,
                   s.status, s.rejection_reason, s.thank_you_message, s.reviewed_at, s.created_at
            FROM submissions s
            WHERE s.firebase_uid = :firebase_uid
        """
        params: dict[str, Any] = {"firebase_uid": firebase_uid}

        if email:
            sql += " OR (s.firebase_uid IS NULL AND LOWER(s.email) = LOWER(:email))"
            params["email"] = email

        sql += " ORDER BY s.created_at DESC"

        try:
            stmt = text(sql)
            result = self._db.execute(stmt, params)
            submissions = []
            for r in result.fetchall():
                d = dict(r._mapping)
                d["id"] = str(d["id"])
                submissions.append(d)
        except Exception as exc:
            err_msg = str(exc).lower()
            if "thank_you_message" in err_msg or "undefinedcolumn" in err_msg or "no such column" in err_msg:
                self._db.rollback()
                fallback_sql = """
                    SELECT s.id, s.publisher_name, s.email, s.firebase_uid, s.details,
                           s.status, s.rejection_reason, s.reviewed_at, s.created_at
                    FROM submissions s
                    WHERE s.firebase_uid = :firebase_uid
                """
                if email:
                    fallback_sql += " OR (s.firebase_uid IS NULL AND LOWER(s.email) = LOWER(:email))"
                fallback_sql += " ORDER BY s.created_at DESC"
                result = self._db.execute(text(fallback_sql), params)
                submissions = []
                for r in result.fetchall():
                    d = dict(r._mapping)
                    d["id"] = str(d["id"])
                    d.setdefault("thank_you_message", None)
                    submissions.append(d)
            else:
                raise


        if not submissions:
            return []

        sub_ids = [s["id"] for s in submissions]

        # 1. Fetch attached files
        files_stmt = text(
            """
            SELECT id, submission_id, original_filename, file_type, file_size, created_at
            FROM submission_files
            WHERE submission_id::text IN :sub_ids
            ORDER BY created_at ASC
            """
        ).bindparams(bindparam("sub_ids", expanding=True))

        files_res = self._db.execute(files_stmt, {"sub_ids": sub_ids})
        files_map: dict[str, list[dict[str, Any]]] = {}
        for r in files_res.fetchall():
            fd = dict(r._mapping)
            fd["id"] = str(fd["id"])
            s_id = str(fd["submission_id"])
            files_map.setdefault(s_id, []).append(fd)

        # 2. Fetch linked published papers
        papers_stmt = text(
            """
            SELECT p.id, p.title, p.submission_id, p.exam_type, p.year, p.paper_type, p.public_url,
                   s.name AS subject_name, c.name AS class_name
            FROM papers p
            LEFT JOIN subjects s ON p.subject_id = s.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE p.submission_id::text IN :sub_ids
            """
        ).bindparams(bindparam("sub_ids", expanding=True))

        try:
            papers_res = self._db.execute(papers_stmt, {"sub_ids": sub_ids})
            papers_map: dict[str, list[dict[str, Any]]] = {}
            for r in papers_res.fetchall():
                pd = dict(r._mapping)
                s_id = str(pd["submission_id"])
                papers_map.setdefault(s_id, []).append(pd)
        except Exception as e:
            logger.debug("Failed to query linked papers for user submissions: %s", e)
            papers_map = {}

        # Merge files and published papers into submissions
        for sub in submissions:
            s_id = sub["id"]
            sub["files"] = files_map.get(s_id, [])
            sub["published_papers"] = papers_map.get(s_id, [])

        return submissions

    def get_user_submission_stats(
        self, firebase_uid: str, email: str | None = None
    ) -> dict[str, int]:
        """
        Return contribution counts for a user: total_submissions, published_count,
        pending_count, rejected_count.
        """
        sql = """
            SELECT status, COUNT(*)::int AS cnt
            FROM submissions
            WHERE firebase_uid = :firebase_uid
        """
        params: dict[str, Any] = {"firebase_uid": firebase_uid}
        if email:
            sql += " OR (firebase_uid IS NULL AND LOWER(email) = LOWER(:email))"
            params["email"] = email

        sql += " GROUP BY status"

        stmt = text(sql)
        stats = {
            "total_submissions": 0,
            "published_count": 0,
            "pending_count": 0,
            "rejected_count": 0,
        }

        try:
            result = self._db.execute(stmt, params)
            for r in result.fetchall():
                status_val = str(r[0]).lower()
                count_val = int(r[1])
                stats["total_submissions"] += count_val
                if status_val == "approved":
                    stats["published_count"] += count_val
                elif status_val == "pending":
                    stats["pending_count"] += count_val
                elif status_val == "rejected":
                    stats["rejected_count"] += count_val
        except Exception as e:
            logger.warning("Failed to calculate user submission stats: %s", e)

        return stats

    # ------------------------------------------------------------------ #
    # Delete submission (admin)
    # ------------------------------------------------------------------ #

    def has_linked_papers(self, submission_id: str) -> bool:
        """Check if any papers reference this submission_id."""
        stmt = text(
            """
            SELECT 1 FROM papers
            WHERE submission_id::text = :submission_id
            LIMIT 1
            """
        )
        row = self._db.execute(stmt, {"submission_id": submission_id}).fetchone()
        return row is not None

    def delete_submission(
        self,
        submission_id: str,
        admin_id: str | None = None,
        admin_email: str | None = None,
    ) -> list[int]:
        """
        Delete a submission, all attached submission_files metadata rows,
        their private storage objects from Supabase Storage, and any
        associated published paper records (and their public CDN storage objects).

        Returns:
            List of deleted paper IDs (if any).
        """
        logger.info(
            "[DELETE_SUBMISSION] START submission_id=%s admin_email=%s",
            submission_id,
            admin_email,
        )

        # ── PHASE A: READ & PLAN ─────────────────────────────────────
        logger.info("[DELETE_SUBMISSION] STEP 1 load submission %s", submission_id)
        sub = self.get_by_id(submission_id)
        if not sub:
            logger.warning("[DELETE_SUBMISSION] Submission %s not found", submission_id)
            return []

        logger.info("[DELETE_SUBMISSION] STEP 2 load linked papers for submission %s", submission_id)
        stmt_papers = text(
            """
            SELECT id, file_path, public_url FROM papers
            WHERE submission_id::text = :submission_id
            """
        )
        paper_rows = self._db.execute(stmt_papers, {"submission_id": submission_id}).fetchall()
        linked_paper_ids: list[int] = []
        paper_storage_paths: list[str] = []

        for r in paper_rows:
            p_dict = dict(r._mapping)
            if p_dict.get("id") is not None:
                linked_paper_ids.append(int(p_dict["id"]))
            f_path = p_dict.get("file_path")
            if not f_path and p_dict.get("public_url") and "/papers/" in p_dict["public_url"]:
                f_path = p_dict["public_url"].split("/papers/")[-1].split("?")[0]
            if f_path:
                paper_storage_paths.append(f_path)

        logger.info(
            "[DELETE_SUBMISSION] STEP 3 load submission files for submission %s (found %d linked papers)",
            submission_id,
            len(linked_paper_ids),
        )
        stmt_files = text(
            """
            SELECT storage_path FROM submission_files
            WHERE submission_id::text = :submission_id
            """
        )
        file_rows = self._db.execute(stmt_files, {"submission_id": submission_id}).fetchall()
        sub_storage_paths = [r[0] for r in file_rows if r[0]]

        # ── PHASE B: STORAGE CLEANUP ─────────────────────────────────
        # 1. Clean up public paper files from 'papers' bucket
        if paper_storage_paths:
            logger.info(
                "[DELETE_SUBMISSION] STEP 4 delete linked paper storage %s",
                paper_storage_paths,
            )
            try:
                self._storage.from_("papers").remove(paper_storage_paths)
            except Exception as p_storage_err:
                logger.warning(
                    "[DELETE_SUBMISSION] Non-fatal storage deletion error on 'papers' bucket for submission %s: %s",
                    submission_id,
                    p_storage_err,
                )

        # 2. Clean up private submission files from 'submissions' bucket
        if sub_storage_paths:
            logger.info(
                "[DELETE_SUBMISSION] STEP 5 delete submission storage %s",
                sub_storage_paths,
            )
            try:
                self._storage.from_(SUBMISSIONS_BUCKET).remove(sub_storage_paths)
            except Exception as sub_storage_err:
                logger.warning(
                    "[DELETE_SUBMISSION] Non-fatal storage deletion error on 'submissions' bucket for submission %s: %s",
                    submission_id,
                    sub_storage_err,
                )

        # ── PHASE C: ATOMIC DATABASE TRANSACTION ─────────────────────
        try:
            # Step 6: Delete linked papers rows
            if linked_paper_ids:
                logger.info(
                    "[DELETE_SUBMISSION] STEP 6 delete linked paper database rows %s",
                    linked_paper_ids,
                )
                del_papers_stmt = text(
                    """
                    DELETE FROM papers
                    WHERE submission_id::text = :submission_id
                    """
                )
                self._db.execute(del_papers_stmt, {"submission_id": submission_id})

            # Step 7: Delete submission_files rows
            logger.info(
                "[DELETE_SUBMISSION] STEP 7 delete submission_files rows for submission %s",
                submission_id,
            )
            del_files_stmt = text(
                """
                DELETE FROM submission_files
                WHERE submission_id::text = :submission_id
                """
            )
            self._db.execute(del_files_stmt, {"submission_id": submission_id})

            # Step 8: Delete submissions row
            logger.info(
                "[DELETE_SUBMISSION] STEP 8 delete submissions row for submission %s",
                submission_id,
            )
            del_sub_stmt = text(
                """
                DELETE FROM submissions
                WHERE id::text = :submission_id
                """
            )
            self._db.execute(del_sub_stmt, {"submission_id": submission_id})

            # Step 9: Insert audit log
            logger.info(
                "[DELETE_SUBMISSION] STEP 9 insert submission audit log for submission %s",
                submission_id,
            )
            audit_stmt = text(
                """
                INSERT INTO audit_logs (admin_id, admin_email, action, target_paper_id, target_details, created_at)
                VALUES (NULL, :admin_email, 'delete_submission', NULL, :details, NOW())
                """
            )
            details = json.dumps(
                {
                    "submission_id": submission_id,
                    "admin_uid": admin_id,
                    "admin_email": admin_email,
                    "publisher_name": sub.get("publisher_name") if sub else None,
                    "email": sub.get("email") if sub else None,
                    "status": sub.get("status") if sub else None,
                    "deleted_paper_ids": linked_paper_ids,
                }
            )
            self._db.execute(
                audit_stmt,
                {
                    "admin_email": admin_email,
                    "details": details,
                },
            )

            # Step 10: Commit atomic transaction
            logger.info("[DELETE_SUBMISSION] STEP 10 COMMIT submission %s", submission_id)
            self._db.commit()
            logger.info("[DELETE_SUBMISSION] SUCCESS submission %s deleted", submission_id)
            return linked_paper_ids
        except Exception as db_err:
            logger.error(
                "[DELETE_SUBMISSION] FAILED stage=database_transaction submission_id=%s exception=%s message=%s",
                submission_id,
                type(db_err).__name__,
                db_err,
                exc_info=True,
            )
            self._db.rollback()
            raise


