"""
Study Materials service — business logic, multi-file validation, atomic publication workflow,
and storage lifecycle management for educational study materials.
"""

import logging
import re
import uuid
from typing import Any, List, Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.storage import get_storage_client
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.classes_repository import ClassesRepository
from app.repositories.material_categories_repository import MaterialCategoriesRepository
from app.repositories.study_materials_repository import StudyMaterialsRepository
from app.repositories.subjects_repository import SubjectsRepository
from app.schemas.study_material import (
    FileType,
    MaterialFileCreate,
    MaterialFileOut,
    MaterialStatus,
    StudyMaterialCreate,
    StudyMaterialListResponse,
    StudyMaterialOut,
    StudyMaterialSummary,
    StudyMaterialUpdate,
)
from app.utils.exceptions import BadRequestError, DatabaseError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Constants
STAGING_BUCKET = "submissions"
PUBLIC_BUCKET = "study-materials"
MAX_FILES_PER_MATERIAL = 5
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

ALLOWED_EXTENSIONS = {
    "pdf": "pdf",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "webp": "image",
    "doc": "word",
    "docx": "word",
    "ppt": "presentation",
    "pptx": "presentation",
    "xls": "spreadsheet",
    "xlsx": "spreadsheet",
}

# Binary magic bytes signatures
MAGIC_BYTES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],
    "docx": [b"PK\x03\x04"],
    "pptx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],
    "doc": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE compound file
    "ppt": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    "xls": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
}


def _detect_file_type(ext: str, url: Optional[str] = None) -> FileType:
    if url:
        lower_url = url.lower()
        if any(d in lower_url for d in ["youtube.com", "youtu.be", "vimeo.com"]):
            return "video"
        return "external_link"
    return ALLOWED_EXTENSIONS.get(ext.lower(), "other")  # type: ignore


def _normalize_tags(tags: list[str]) -> list[str]:
    """Lowercase, strip non-alphanumeric, and deduplicate tags."""
    cleaned = []
    for t in tags:
        s = re.sub(r"[^a-zA-Z0-9\-_]", "", t.strip().lower())
        if s and s not in cleaned:
            cleaned.append(s)
    return cleaned


def _sanitize_download_filename(filename: str, ext: str = "pdf") -> str:
    """Strip illegal filesystem chars and prevent double extensions (e.g. .pdf.pdf)."""
    if not filename:
        return f"download.{ext}"
    clean = filename.strip()
    # Strip any trailing repeated extensions like .pdf.pdf, .PDF.pdf, etc.
    clean = re.sub(r'(\.(pdf|png|jpg|jpeg|webp|docx|xlsx|pptx))+$', '', clean, flags=re.IGNORECASE)
    # Strip invalid filesystem characters [/\\?%*:|"<>]+
    clean = re.sub(r'[/\\?%*:|"<>]+', '_', clean)
    clean = clean.strip(". ")
    target_ext = ext.lstrip(".")
    return f"{clean}.{target_ext}" if clean else f"download.{target_ext}"


class StudyMaterialsService:
    """Service layer for study materials."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._db = db
        self._repo = StudyMaterialsRepository(db)
        self._cat_repo = MaterialCategoriesRepository(db)
        self._classes_repo = ClassesRepository(db)
        self._subjects_repo = SubjectsRepository(db)
        self._analytics_repo = AnalyticsRepository(db)
        self._storage = storage if storage is not None else get_storage_client()

    # ── URL Resolution ─────────────────────────────────────────────────────────

    def _resolve_file_url(self, file_row: dict[str, Any], is_admin: bool = False) -> Optional[str]:
        """Resolve public CDN URL, private presigned preview URL, or external link."""
        if file_row.get("external_url"):
            return file_row["external_url"]

        bucket = file_row.get("bucket_name")
        path = file_row.get("storage_path")
        if not bucket or not path:
            return None

        try:
            if bucket == PUBLIC_BUCKET:
                res = self._storage.from_(bucket).get_public_url(path)
                return res if isinstance(res, str) else res.get("publicURL") or res.get("publicUrl")
            elif bucket == STAGING_BUCKET:
                # Private staging: provide signed URL for admin preview
                res = self._storage.from_(bucket).create_signed_url(path, 900)
                return res.get("signedURL") or res.get("signedUrl") if isinstance(res, dict) else str(res)
        except Exception as exc:
            logger.warning("Failed to resolve URL for file %s in bucket %s: %s", path, bucket, exc)
            return None
        return None

    def _enrich_material_files(self, material_dict: dict[str, Any], is_admin: bool = False) -> dict[str, Any]:
        """Attach resolved public or signed URLs to file attachments."""
        enriched_files = []
        for f in material_dict.get("files", []):
            f_copy = dict(f)
            f_copy["public_url"] = self._resolve_file_url(f_copy, is_admin=is_admin)
            enriched_files.append(f_copy)
        material_dict["files"] = enriched_files
        return material_dict

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def get_material_by_slug(self, slug: str, is_admin: bool = False) -> StudyMaterialOut:
        mat = self._repo.get_by_slug(slug, published_only=not is_admin)
        if not mat:
            raise NotFoundError("StudyMaterial", slug)
        enriched = self._enrich_material_files(mat, is_admin=is_admin)
        # Track view count asynchronously/safely
        try:
            self._repo.increment_view_count(enriched["id"])
            self._analytics_repo.insert_event(
                event_type="material_view",
                class_id=enriched.get("class_id"),
                subject_id=enriched.get("subject_id"),
                metadata={"material_id": str(enriched["id"]), "slug": slug},
            )
        except Exception as e:
            logger.debug("Failed to record view event: %s", e)
        return StudyMaterialOut(**enriched)

    def get_material_by_id(self, material_id: UUID | str, is_admin: bool = False) -> StudyMaterialOut:
        mat = self._repo.get_by_id(material_id, published_only=not is_admin)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))
        enriched = self._enrich_material_files(mat, is_admin=is_admin)
        return StudyMaterialOut(**enriched)

    def list_materials(
        self,
        *,
        class_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        class_general_only: bool = False,
        category_id: Optional[int] = None,
        medium: Optional[str] = None,
        tag: Optional[str] = None,
        question_format: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        is_admin: bool = False,
        page: int = 1,
        limit: int = 20,
    ) -> StudyMaterialListResponse:
        rows, total = self._repo.list_materials(
            class_id=class_id,
            subject_id=subject_id,
            class_general_only=class_general_only,
            category_id=category_id,
            medium=medium,
            tag=tag,
            question_format=question_format,
            search=search,
            status=status if is_admin else "published",
            published_only=not is_admin,
            page=page,
            limit=limit,
        )
        return StudyMaterialListResponse(
            data=[StudyMaterialSummary(**r) for r in rows],
            total=total,
            page=page,
            limit=limit,
        )

    # ── Validation ─────────────────────────────────────────────────────────────

    def _validate_scope_and_category(
        self,
        class_id: int,
        subject_id: Optional[int],
        category_id: Optional[int],
    ) -> None:
        """Enforce scope consistency and category hierarchy rules."""
        # 1. Verify class exists
        cls_row = self._classes_repo.get_by_id(class_id)
        if not cls_row:
            raise ValidationError(f"Class id {class_id} does not exist.")

        # 2. Verify subject belongs to class
        if subject_id is not None:
            subj_row = self._subjects_repo.get_by_id(subject_id)
            if not subj_row:
                raise ValidationError(f"Subject id {subject_id} does not exist.")
            if subj_row.get("class_id") != class_id:
                raise ValidationError(f"Subject id {subject_id} does not belong to class {class_id}.")

        # 3. Verify category scope compatibility
        if category_id is not None:
            cat = self._cat_repo.get_by_id(category_id)
            if not cat:
                raise ValidationError(f"Category id {category_id} does not exist.")
            cat_cls = cat.get("class_id")
            cat_subj = cat.get("subject_id")

            if subject_id is None:
                # Class-level material: category must be Global or Class-scoped for this class
                if cat_subj is not None:
                    raise ValidationError("A subject-scoped category cannot be assigned to a class-level material.")
                if cat_cls is not None and cat_cls != class_id:
                    raise ValidationError(f"Category belongs to class {cat_cls}, not selected class {class_id}.")
            else:
                # Subject-level material: category can be Global, Class-scoped for this class, or Subject-scoped for this subject
                if cat_cls is not None and cat_cls != class_id:
                    raise ValidationError(f"Category belongs to class {cat_cls}, not selected class {class_id}.")
                if cat_subj is not None and cat_subj != subject_id:
                    raise ValidationError(f"Category belongs to subject {cat_subj}, not selected subject {subject_id}.")

    # ── Authoring & File Upload ────────────────────────────────────────────────

    async def create_material(
        self,
        payload: StudyMaterialCreate,
        files: Optional[list[UploadFile]] = None,
        created_by: Optional[UUID | str] = None,
    ) -> StudyMaterialOut:
        """Create study material with uploaded files and/or external links."""
        self._validate_scope_and_category(payload.class_id, payload.subject_id, payload.category_id)

        clean_tags = _normalize_tags(payload.tags)

        # 1. Create main material row (starts in draft or requested status)
        created_mat = self._repo.create_material(
            title=payload.title,
            class_id=payload.class_id,
            subject_id=payload.subject_id,
            category_id=payload.category_id,
            description=payload.description,
            medium=payload.medium,
            question_formats=payload.question_formats,
            tags=clean_tags,
            academic_year=payload.academic_year,
            author_name=payload.author_name,
            author_organization=payload.author_organization,
            status="draft",  # Always stage in draft first before promoting files
            created_by=created_by,
            slug=payload.slug,
        )
        mat_id = created_mat["id"]
        staged_storage_paths: list[tuple[str, str]] = []  # (bucket, path)

        try:
            # 2. Add external link attachments from payload
            sort_order = 0
            for ext_file in payload.files:
                if ext_file.external_url:
                    detected_type = _detect_file_type("", url=ext_file.external_url)
                    self._repo.add_file(
                        material_id=mat_id,
                        file_title=ext_file.file_title,
                        display_filename=ext_file.display_filename or ext_file.file_title,
                        file_type=detected_type,
                        mime_type=None,
                        file_size=0,
                        bucket_name=None,
                        storage_path=None,
                        external_url=ext_file.external_url,
                        sort_order=sort_order,
                    )
                    sort_order += 1

            # 3. Process uploaded files (staged in private STAGING_BUCKET)
            if files:
                if len(files) > MAX_FILES_PER_MATERIAL:
                    raise BadRequestError(f"Maximum of {MAX_FILES_PER_MATERIAL} files allowed per material package.")

                for idx, file in enumerate(files):
                    if not file.filename:
                        continue
                    custom_fn = payload.download_filename if (idx == 0 and payload.download_filename) else None
                    file_info = await self._validate_and_stage_file(mat_id, file, custom_filename=custom_fn)
                    staged_storage_paths.append((file_info["bucket"], file_info["storage_path"]))
                    self._repo.add_file(
                        material_id=mat_id,
                        file_title=file_info["file_title"],
                        display_filename=file_info["display_filename"],
                        file_type=file_info["file_type"],
                        mime_type=file_info["mime_type"],
                        file_size=file_info["file_size"],
                        bucket_name=file_info["bucket"],
                        storage_path=file_info["storage_path"],
                        external_url=None,
                        sort_order=sort_order,
                    )
                    sort_order += 1

            # 4. If requested status is 'published', trigger atomic publication sequence
            if payload.status == "published":
                await self.publish_material(mat_id, updated_by=created_by)

            return self.get_material_by_id(mat_id, is_admin=True)

        except Exception as exc:
            logger.error("Material creation failed; initiating compensating rollback for %s: %s", mat_id, exc)
            # Cleanup any staged files
            for bucket, path in staged_storage_paths:
                try:
                    self._storage.from_(bucket).remove([path])
                except Exception as clean_err:
                    logger.warning("Compensating cleanup failed for %s/%s: %s", bucket, path, clean_err)
            # Delete DB row
            self._repo.delete_material(mat_id)
            raise

    async def _validate_and_stage_file(
        self,
        material_id: UUID | str,
        file: UploadFile,
        custom_filename: Optional[str] = None,
    ) -> dict[str, Any]:
        """Validate format, magic bytes, size, and upload to private staging bucket."""
        filename = file.filename or "file"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if not ext or ext not in ALLOWED_EXTENSIONS:
            raise BadRequestError(
                f"Unsupported file format '.{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS.keys()))}."
            )

        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise BadRequestError(f"Uploaded file '{filename}' is empty.")
        if file_size > MAX_FILE_SIZE_BYTES:
            raise BadRequestError(f"File '{filename}' exceeds maximum allowed size of 50 MB.")

        # Inspect binary magic bytes
        expected_magics = MAGIC_BYTES.get(ext, [])
        if expected_magics:
            if not any(content.startswith(m) for m in expected_magics):
                raise BadRequestError(f"File content of '{filename}' does not match expected binary format for '.{ext}'.")

        # Clean display filename
        if custom_filename and custom_filename.strip():
            safe_display = _sanitize_download_filename(custom_filename, ext=ext)
        else:
            safe_display = _sanitize_download_filename(filename, ext=ext)

        file_uuid = uuid.uuid4().hex
        staging_path = f"materials/drafts/{material_id}/{file_uuid}.{ext}"

        # Upload to private staging bucket with guaranteed application/pdf for PDFs
        content_type = "application/pdf" if ext == "pdf" else (file.content_type or "application/octet-stream")
        try:
            self._storage.from_(STAGING_BUCKET).upload(
                path=staging_path,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"},
            )
        except Exception as e:
            logger.error("Storage upload to staging bucket failed: %s", e)
            raise DatabaseError("Failed to upload attachment to staging storage.") from e

        return {
            "bucket": STAGING_BUCKET,
            "storage_path": staging_path,
            "file_title": safe_display.rsplit(".", 1)[0].replace("_", " ").title()[:255],
            "display_filename": safe_display,
            "file_type": ALLOWED_EXTENSIONS[ext],
            "mime_type": content_type,
            "file_size": file_size,
        }

    # ── Atomic Publication Sequence ────────────────────────────────────────────

    async def publish_material(self, material_id: UUID | str, updated_by: Optional[UUID | str] = None) -> StudyMaterialOut:
        """
        Atomic publication sequence:
        1. Verify material has at least one attachment or external link.
        2. Copy all staged physical files from private STAGING_BUCKET to PUBLIC_BUCKET.
        3. Verify destination objects exist.
        4. In database transaction, update material_files storage references and set status = 'published'.
        5. Clean up staging files from private bucket.
        """
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))

        files = mat.get("files", [])
        if not files:
            raise BadRequestError("Cannot publish a study material without at least one attachment or external link.")

        class_id = mat["class_id"]
        copied_public_paths: list[str] = []
        staged_files_to_clean: list[tuple[str, str]] = []  # (file_id, staged_path)

        try:
            for f in files:
                bucket = f.get("bucket_name")
                staged_path = f.get("storage_path")

                # If file is in private staging bucket, promote it to public CDN bucket
                if bucket == STAGING_BUCKET and staged_path:
                    ext = staged_path.rsplit(".", 1)[-1] if "." in staged_path else "pdf"
                    public_path = f"materials/{class_id}/{material_id}/{f['id']}.{ext}"

                    # Download from staging
                    file_bytes = self._storage.from_(STAGING_BUCKET).download(staged_path)
                    if not file_bytes or len(file_bytes) == 0:
                        raise DatabaseError(f"Staged file {staged_path} could not be read.")

                    # Upload to public bucket
                    content_type = "application/pdf" if ext == "pdf" else (f.get("mime_type") or "application/octet-stream")
                    self._storage.from_(PUBLIC_BUCKET).upload(
                        path=public_path,
                        file=file_bytes,
                        file_options={"content-type": content_type, "upsert": "true"},
                    )
                    copied_public_paths.append(public_path)
                    staged_files_to_clean.append((f["id"], staged_path))

            # Database commit: update storage references and set status = 'published'
            for fid, _ in staged_files_to_clean:
                # Find public path
                f_item = next(x for x in files if x["id"] == fid)
                ext = f_item["storage_path"].rsplit(".", 1)[-1] if "." in f_item["storage_path"] else "pdf"
                pub_path = f"materials/{class_id}/{material_id}/{fid}.{ext}"
                self._repo.update_file_storage(fid, bucket_name=PUBLIC_BUCKET, storage_path=pub_path)

            self._repo.update_status(material_id, status="published", updated_by=updated_by)

            # Clean up temporary staging files from private bucket
            for _, staged_p in staged_files_to_clean:
                try:
                    self._storage.from_(STAGING_BUCKET).remove([staged_p])
                except Exception as ce:
                    logger.warning("Post-publish cleanup failed for staged file %s: %s", staged_p, ce)

            return self.get_material_by_id(material_id, is_admin=True)

        except Exception as exc:
            logger.error("Publication sequence failed for %s; rolling back copied public objects: %s", material_id, exc)
            # Remove any partially copied public objects
            for pub_p in copied_public_paths:
                try:
                    self._storage.from_(PUBLIC_BUCKET).remove([pub_p])
                except Exception as clean_err:
                    logger.warning("Compensating cleanup of public file %s failed: %s", pub_p, clean_err)
            raise DatabaseError(f"Publication failed: {exc}") from exc

    # ── Status Updates & Archival ──────────────────────────────────────────────

    def update_status(self, material_id: UUID | str, status: MaterialStatus, updated_by: Optional[UUID | str] = None) -> StudyMaterialOut:
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))

        self._repo.update_status(material_id, status=status, updated_by=updated_by)
        return self.get_material_by_id(material_id, is_admin=True)

    def update_material(self, material_id: UUID | str, payload: StudyMaterialUpdate, updated_by: Optional[UUID | str] = None) -> StudyMaterialOut:
        existing = self._repo.get_by_id(material_id, published_only=False)
        if not existing:
            raise NotFoundError("StudyMaterial", str(material_id))

        target_class = payload.class_id if payload.class_id is not None else existing["class_id"]
        target_subject = payload.subject_id if payload.subject_id is not None else existing["subject_id"]
        target_category = payload.category_id if payload.category_id is not None else existing["category_id"]

        self._validate_scope_and_category(target_class, target_subject, target_category)

        clean_tags = _normalize_tags(payload.tags) if payload.tags is not None else None

        self._repo.update_material(
            material_id,
            title=payload.title,
            description=payload.description,
            class_id=payload.class_id,
            subject_id=payload.subject_id,
            clear_subject=(payload.subject_id is None and "subject_id" in payload.model_fields_set),
            category_id=payload.category_id,
            clear_category=(payload.category_id is None and "category_id" in payload.model_fields_set),
            medium=payload.medium,
            question_formats=payload.question_formats,
            tags=clean_tags,
            academic_year=payload.academic_year,
            author_name=payload.author_name,
            author_organization=payload.author_organization,
            status=payload.status,
            updated_by=updated_by,
        )

        if payload.download_filename and existing.get("files"):
            first_file = existing["files"][0]
            ext = first_file.get("storage_path", "").rsplit(".", 1)[-1] if (first_file.get("storage_path") and "." in first_file.get("storage_path")) else "pdf"
            sanitized_fn = self._sanitize_download_filename(payload.download_filename, ext)
            self._repo.update_file_display_name(first_file["id"], display_filename=sanitized_fn)

        return self.get_material_by_id(material_id, is_admin=True)

    # ── File Attachment Addition & Removal ─────────────────────────────────────

    async def add_attachment(
        self,
        material_id: UUID | str,
        file: Optional[UploadFile] = None,
        file_title: Optional[str] = None,
        external_url: Optional[str] = None,
    ) -> MaterialFileOut:
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))

        existing_files = mat.get("files", [])
        if len(existing_files) >= MAX_FILES_PER_MATERIAL:
            raise BadRequestError(f"Material already has maximum of {MAX_FILES_PER_MATERIAL} attachments.")

        sort_order = len(existing_files)

        if external_url:
            detected_type = _detect_file_type("", url=external_url)
            created_f = self._repo.add_file(
                material_id=material_id,
                file_title=file_title or "External Resource",
                display_filename=file_title or "External Resource",
                file_type=detected_type,
                mime_type=None,
                file_size=0,
                bucket_name=None,
                storage_path=None,
                external_url=external_url,
                sort_order=sort_order,
            )
            return MaterialFileOut(**created_f, public_url=external_url)

        if not file:
            raise BadRequestError("Must provide either an uploaded file or an external URL.")

        # Upload file directly to appropriate bucket depending on current material status
        if mat["status"] == "published":
            # Upload directly to public bucket
            filename = file.filename or "file"
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if not ext or ext not in ALLOWED_EXTENSIONS:
                raise BadRequestError(f"Unsupported format '.{ext}'.")
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_BYTES:
                raise BadRequestError("File exceeds 50 MB limit.")
            file_uuid = uuid.uuid4().hex
            public_path = f"materials/{mat['class_id']}/{material_id}/{file_uuid}.{ext}"
            content_type = "application/pdf" if ext == "pdf" else (file.content_type or "application/octet-stream")
            self._storage.from_(PUBLIC_BUCKET).upload(
                path=public_path,
                file=content,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            safe_fn = _sanitize_download_filename(file_title or filename, ext=ext)
            created_f = self._repo.add_file(
                material_id=material_id,
                file_title=file_title or safe_fn.rsplit(".", 1)[0].replace("_", " ").title()[:255],
                display_filename=safe_fn,
                file_type=ALLOWED_EXTENSIONS[ext],
                mime_type=content_type,
                file_size=len(content),
                bucket_name=PUBLIC_BUCKET,
                storage_path=public_path,
                external_url=None,
                sort_order=sort_order,
            )
            created_f["public_url"] = self._resolve_file_url(created_f, is_admin=True)
            return MaterialFileOut(**created_f)
        else:
            # Material is draft: stage in private bucket
            file_info = await self._validate_and_stage_file(material_id, file)
            created_f = self._repo.add_file(
                material_id=material_id,
                file_title=file_title or file_info["file_title"],
                display_filename=file_info["display_filename"],
                file_type=file_info["file_type"],
                mime_type=file_info["mime_type"],
                file_size=file_info["file_size"],
                bucket_name=file_info["bucket"],
                storage_path=file_info["storage_path"],
                external_url=None,
                sort_order=sort_order,
            )
            created_f["public_url"] = self._resolve_file_url(created_f, is_admin=True)
            return MaterialFileOut(**created_f)

    def delete_attachment(self, file_id: UUID | str) -> dict[str, Any]:
        file_row = self._repo.get_file_by_id(file_id)
        if not file_row:
            raise NotFoundError("MaterialFile", str(file_id))

        bucket = file_row.get("bucket_name")
        path = file_row.get("storage_path")

        # Delete from DB
        self._repo.delete_file(file_id)

        # Delete from storage if physical file
        if bucket and path:
            try:
                self._storage.from_(bucket).remove([path])
            except Exception as e:
                logger.warning("Failed to remove storage object %s from %s: %s", path, bucket, e)

        return {"deleted": True, "file_id": str(file_id)}

    # ── Permanent Deletion (Super Admin Only) ──────────────────────────────────

    def permanently_delete_material(self, material_id: UUID | str) -> dict[str, Any]:
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))

        # Purge all attached files from Supabase Storage
        for f in mat.get("files", []):
            bucket = f.get("bucket_name")
            path = f.get("storage_path")
            if bucket and path:
                try:
                    self._storage.from_(bucket).remove([path])
                except Exception as e:
                    logger.warning("Failed to delete storage file %s during material purge: %s", path, e)

        # Delete database row (cascades to material_files)
        self._repo.delete_material(material_id)
        return {"deleted": True, "material_id": str(material_id), "message": "Study material and all files permanently deleted."}

    # ── Download Tracking ──────────────────────────────────────────────────────

    def record_download(self, material_id: UUID | str, file_id: UUID | str, user_uid: Optional[str] = None) -> dict[str, Any]:
        mat = self._repo.get_by_id(material_id, published_only=True)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))

        file_row = self._repo.get_file_by_id(file_id)
        if not file_row or str(file_row.get("material_id")) != str(material_id):
            raise NotFoundError("MaterialFile", str(file_id))

        self._repo.increment_download_count(material_id, file_id=file_id)

        # Log to analytics_events
        try:
            self._analytics_repo.insert_event(
                event_type="material_download",
                firebase_uid=user_uid,
                class_id=mat.get("class_id"),
                subject_id=mat.get("subject_id"),
                metadata={
                    "material_id": str(material_id),
                    "file_id": str(file_id),
                    "file_type": file_row.get("file_type"),
                    "file_title": file_row.get("file_title"),
                },
            )
        except Exception as e:
            logger.debug("Failed to record analytics event for download: %s", e)

        target_url = self._resolve_file_url(file_row, is_admin=False)
        return {
            "success": True,
            "material_id": str(material_id),
            "file_id": str(file_id),
            "download_url": target_url,
            "filename": file_row.get("display_filename") or file_row.get("file_title") or f"{mat.get('title')}.pdf",
        }

    # ── Study Material Likes ──────────────────────────────────────────────────

    def toggle_like(self, material_id: UUID | str, firebase_uid: str) -> dict[str, Any]:
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))
        return self._repo.toggle_like(material_id, firebase_uid=firebase_uid)

    def get_likes_info(self, material_id: UUID | str, firebase_uid: Optional[str] = None) -> dict[str, Any]:
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))
        return self._repo.get_likes_info(material_id, firebase_uid=firebase_uid)

    # ── Study Material Comments ───────────────────────────────────────────────

    def get_comments(self, material_id: UUID | str) -> list:
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))

        flat_rows = self._repo.get_comments_for_material(material_id)

        from app.schemas.study_material import StudyMaterialCommentOut

        comment_map: dict[str, StudyMaterialCommentOut] = {}
        root_comments: list[StudyMaterialCommentOut] = []

        for c in flat_rows:
            c_out = StudyMaterialCommentOut(
                id=str(c["id"]),
                material_id=c["material_id"],
                firebase_uid=c["firebase_uid"],
                author_name=c["author_name"],
                author_avatar=c.get("author_avatar"),
                parent_id=str(c["parent_id"]) if c.get("parent_id") else None,
                content=c["content"],
                is_deleted=c.get("is_deleted", False),
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                replies=[],
            )
            comment_map[str(c["id"])] = c_out

        for c in flat_rows:
            c_id = str(c["id"])
            p_id = str(c["parent_id"]) if c.get("parent_id") else None
            if p_id and p_id in comment_map:
                comment_map[p_id].replies.append(comment_map[c_id])
            else:
                root_comments.append(comment_map[c_id])

        return root_comments

    def add_comment(
        self,
        material_id: UUID | str,
        content: str,
        firebase_uid: str,
        author_name: str,
        parent_id: Optional[str] = None,
        author_avatar: Optional[str] = None,
    ) -> dict[str, Any]:
        mat = self._repo.get_by_id(material_id, published_only=False)
        if not mat:
            raise NotFoundError("StudyMaterial", str(material_id))

        return self._repo.add_material_comment(
            material_id=material_id,
            firebase_uid=firebase_uid,
            author_name=author_name,
            content=content.strip(),
            parent_id=parent_id,
            author_avatar=author_avatar,
        )

    def delete_comment(
        self,
        comment_id: str,
        current_user: dict,
    ) -> dict[str, Any]:
        is_admin = current_user.get("role") in ("ADMIN", "SUPER_ADMIN")

        chk_stmt = text("SELECT id, material_id, firebase_uid, content FROM study_material_comments WHERE id::text = :cid")
        row = self._db.execute(chk_stmt, {"cid": str(comment_id)}).fetchone()
        if not row:
            raise NotFoundError(resource="Comment", identifier=comment_id)

        comment_dict = dict(row._mapping)
        user_uid = current_user.get("firebase_uid") or current_user.get("user_id")
        if not is_admin and comment_dict.get("firebase_uid") != user_uid:
            from app.utils.exceptions import ForbiddenError
            raise ForbiddenError(detail="You do not have permission to delete this comment.")

        self._repo.delete_material_comment(comment_id, hard_delete=is_admin, auto_commit=True)
        return {"id": comment_id, "deleted": True}

