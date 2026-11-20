"""
Study Materials API endpoints.
Provides public access to published study materials and full admin authoring/moderation capabilities.
"""

import json
import logging
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user, get_current_user_optional, require_admin, require_role, require_super_admin
from app.dependencies.supabase import get_db
from app.schemas.study_material import (
    MaterialFileOut,
    MaterialStatusUpdate,
    StudyMaterialCreate,
    StudyMaterialListResponse,
    StudyMaterialOut,
    StudyMaterialUpdate,
    StudyMaterialLikeResponse,
    StudyMaterialCommentCreate,
    StudyMaterialCommentOut,
)
from app.services.study_materials_service import StudyMaterialsService
from app.utils.exceptions import BadRequestError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Study Materials"])


# ── Public Endpoints ──────────────────────────────────────────────────────────

@router.get(
    "/study-materials",
    response_model=StudyMaterialListResponse,
    summary="List published study materials",
)
def list_published_materials(
    class_id: Annotated[Optional[int], Query(description="Filter by class ID")] = None,
    subject_id: Annotated[Optional[int], Query(description="Filter by subject ID")] = None,
    category_id: Annotated[Optional[int], Query(description="Filter by category ID")] = None,
    medium: Annotated[Optional[str], Query(description="Filter by medium ('tamil', 'english', 'both')")] = None,
    tag: Annotated[Optional[str], Query(description="Filter by tag")] = None,
    question_format: Annotated[Optional[str], Query(description="Filter by question format")] = None,
    search: Annotated[Optional[str], Query(description="Search title, description, or author")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
) -> StudyMaterialListResponse:
    """Returns only published study materials with applied filters."""
    service = StudyMaterialsService(db)
    return service.list_materials(
        class_id=class_id,
        subject_id=subject_id,
        category_id=category_id,
        medium=medium,
        tag=tag,
        question_format=question_format,
        search=search,
        is_admin=False,
        page=page,
        limit=limit,
    )


@router.get(
    "/study-materials/by-subject/{subject_id}",
    response_model=StudyMaterialListResponse,
    summary="List published materials for a specific subject",
)
def list_materials_by_subject(
    subject_id: int,
    category_id: Annotated[Optional[int], Query()] = None,
    medium: Annotated[Optional[str], Query()] = None,
    tag: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
) -> StudyMaterialListResponse:
    service = StudyMaterialsService(db)
    return service.list_materials(
        subject_id=subject_id,
        category_id=category_id,
        medium=medium,
        tag=tag,
        is_admin=False,
        page=page,
        limit=limit,
    )


@router.get(
    "/study-materials/class-general/{class_id}",
    response_model=StudyMaterialListResponse,
    summary="List class-level general materials (subject_id IS NULL)",
)
def list_class_general_materials(
    class_id: int,
    category_id: Annotated[Optional[int], Query()] = None,
    medium: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
) -> StudyMaterialListResponse:
    service = StudyMaterialsService(db)
    return service.list_materials(
        class_id=class_id,
        class_general_only=True,
        category_id=category_id,
        medium=medium,
        is_admin=False,
        page=page,
        limit=limit,
    )


@router.get(
    "/study-materials/{slug}",
    response_model=StudyMaterialOut,
    summary="Get single published study material detail by slug",
)
def get_material_by_slug(
    slug: str,
    db: Session = Depends(get_db),
) -> StudyMaterialOut:
    """Returns single published material detail and increments view counter."""
    service = StudyMaterialsService(db)
    return service.get_material_by_slug(slug, is_admin=False)


@router.post(
    "/study-materials/{material_id}/files/{file_id}/download",
    summary="Track download count and get file download URL",
)
def track_and_download_file(
    material_id: UUID,
    file_id: UUID,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> dict:
    service = StudyMaterialsService(db)
    user_uid = current_user.get("firebase_uid") if current_user else None
    return service.record_download(material_id, file_id, user_uid=user_uid)


# ── Study Material Likes & Comments Endpoints ─────────────────────────────────

@router.post(
    "/study-materials/{material_id}/like",
    response_model=StudyMaterialLikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle like on a study material",
    description="Authenticated endpoint. Toggles like/unlike for the authenticated Firebase user.",
)
async def toggle_material_like(
    material_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyMaterialLikeResponse:
    service = StudyMaterialsService(db)
    res = service.toggle_like(material_id, firebase_uid=current_user["firebase_uid"])
    return StudyMaterialLikeResponse(**res)


@router.get(
    "/study-materials/{material_id}/likes",
    response_model=StudyMaterialLikeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get study material likes count and user status",
    description="Public endpoint. Returns like count and whether the optional current user liked it.",
)
async def get_material_likes(
    material_id: UUID,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
) -> StudyMaterialLikeResponse:
    service = StudyMaterialsService(db)
    uid = current_user.get("firebase_uid") if current_user else None
    res = service.get_likes_info(material_id, firebase_uid=uid)
    return StudyMaterialLikeResponse(**res)


@router.get(
    "/study-materials/{material_id}/comments",
    response_model=list[StudyMaterialCommentOut],
    status_code=status.HTTP_200_OK,
    summary="Get study material comments",
    description="Public endpoint. Returns threaded comments for a study material.",
)
async def get_material_comments(
    material_id: UUID,
    db: Session = Depends(get_db),
) -> list[StudyMaterialCommentOut]:
    service = StudyMaterialsService(db)
    return service.get_comments(material_id)


@router.post(
    "/study-materials/{material_id}/comments",
    response_model=StudyMaterialCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to study material",
    description="Authenticated endpoint. Adds a comment or nested reply to a study material.",
)
async def add_material_comment(
    material_id: UUID,
    req: StudyMaterialCommentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyMaterialCommentOut:
    service = StudyMaterialsService(db)
    author_name = current_user.get("display_name") or current_user.get("email", "").split("@")[0] or "Student"
    res = service.add_comment(
        material_id=material_id,
        content=req.content,
        firebase_uid=current_user["firebase_uid"],
        author_name=author_name,
        parent_id=req.parent_id,
        author_avatar=req.author_avatar,
    )
    return StudyMaterialCommentOut(
        id=str(res["id"]),
        material_id=res["material_id"],
        firebase_uid=res["firebase_uid"],
        author_name=res["author_name"],
        author_avatar=res.get("author_avatar"),
        parent_id=res.get("parent_id"),
        content=res["content"],
        is_deleted=res.get("is_deleted", False),
        created_at=res["created_at"],
        updated_at=res["updated_at"],
        replies=[],
    )


@router.delete(
    "/study-materials/comments/{comment_id}",
    summary="Delete a study material comment",
    description="Authenticated endpoint. Deletes a comment (owner or admin).",
)
async def delete_material_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = StudyMaterialsService(db)
    return service.delete_comment(comment_id, current_user=current_user)


# ── Admin Endpoints (require_role(["ADMIN", "SUPER_ADMIN"])) ──────────────────

@router.get(
    "/admin/study-materials",
    response_model=StudyMaterialListResponse,
    summary="List all study materials including drafts and archived (Admin)",
)
def list_materials_admin(
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    class_id: Annotated[Optional[int], Query()] = None,
    subject_id: Annotated[Optional[int], Query()] = None,
    category_id: Annotated[Optional[int], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StudyMaterialListResponse:
    service = StudyMaterialsService(db)
    return service.list_materials(
        class_id=class_id,
        subject_id=subject_id,
        category_id=category_id,
        status=status_filter,
        search=search,
        is_admin=True,
        page=page,
        limit=limit,
    )


@router.get(
    "/admin/study-materials/{material_id}",
    response_model=StudyMaterialOut,
    summary="Get study material detail for editing (Admin)",
)
def get_material_admin(
    material_id: UUID,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StudyMaterialOut:
    service = StudyMaterialsService(db)
    return service.get_material_by_id(material_id, is_admin=True)


@router.post(
    "/admin/study-materials",
    response_model=StudyMaterialOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new study material with attachments (Admin)",
)
async def create_material_admin(
    payload: Annotated[str, Form(description="JSON-encoded StudyMaterialCreate payload")],
    files: Annotated[List[UploadFile], File(description="Uploaded attachment files")] = [],
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StudyMaterialOut:
    try:
        data = json.loads(payload)
        create_schema = StudyMaterialCreate(**data)
    except Exception as e:
        raise BadRequestError(f"Invalid JSON payload: {e}")

    admin_user_id = admin.get("id")
    service = StudyMaterialsService(db)
    return await service.create_material(create_schema, files=files, created_by=admin_user_id)


@router.put(
    "/admin/study-materials/{material_id}",
    response_model=StudyMaterialOut,
    summary="Update study material metadata (Admin)",
)
def update_material_admin(
    material_id: UUID,
    payload: StudyMaterialUpdate,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StudyMaterialOut:
    admin_user_id = admin.get("id")
    service = StudyMaterialsService(db)
    return service.update_material(material_id, payload, updated_by=admin_user_id)


@router.patch(
    "/admin/study-materials/{material_id}/status",
    response_model=StudyMaterialOut,
    summary="Change publication status: draft, published, archived (Admin)",
)
async def update_material_status_admin(
    material_id: UUID,
    payload: MaterialStatusUpdate,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StudyMaterialOut:
    admin_user_id = admin.get("id")
    service = StudyMaterialsService(db)
    if payload.status == "published":
        return await service.publish_material(material_id, updated_by=admin_user_id)
    return service.update_status(material_id, payload.status, updated_by=admin_user_id)


@router.post(
    "/admin/study-materials/{material_id}/files",
    response_model=MaterialFileOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add an attachment or external link to an existing material (Admin)",
)
async def add_attachment_admin(
    material_id: UUID,
    file: Annotated[Optional[UploadFile], File()] = None,
    file_title: Annotated[Optional[str], Form()] = None,
    external_url: Annotated[Optional[str], Form()] = None,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MaterialFileOut:
    service = StudyMaterialsService(db)
    return await service.add_attachment(
        material_id,
        file=file,
        file_title=file_title,
        external_url=external_url,
    )


@router.delete(
    "/admin/study-materials/{material_id}/files/{file_id}",
    summary="Delete an attachment from material (Admin)",
)
def delete_attachment_admin(
    material_id: UUID,
    file_id: UUID,
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = StudyMaterialsService(db)
    return service.delete_attachment(file_id)


@router.delete(
    "/admin/study-materials/{material_id}",
    summary="Permanently delete study material and purge files (Super Admin Only)",
)
def permanently_delete_material_admin(
    material_id: UUID,
    _super_admin: dict = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> dict:
    service = StudyMaterialsService(db)
    return service.permanently_delete_material(material_id)
