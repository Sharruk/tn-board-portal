"""
Tests for Study Materials endpoints and service:
  - Public listing, detail by slug, subject/class filters, download tracking
  - Admin creation (class-level vs subject-level), drafts, multi-file attachments, external links
  - Scope validation (subject must belong to class)
  - Lifecycle: draft -> published -> archived -> restored
  - Draft privacy (anonymous access returns 404)
  - Role protection (Superadmin permanent deletion)
"""

import io
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user, get_current_user_optional, require_admin, require_role, require_super_admin
from app.dependencies.supabase import get_db
from app.main import app
from app.services.study_materials_service import StudyMaterialsService


class MockRow:
    def __init__(self, data: dict):
        self._mapping = data

    def __getitem__(self, key):
        return self._mapping[key]

    def get(self, key, default=None):
        return self._mapping.get(key, default)


class MockResult:
    def __init__(self, rows: list[dict] | None = None, scalar_val=None, rowcount: int = 1):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


SAMPLE_FILE = {
    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "material_id": "11111111-1111-1111-1111-111111111111",
    "file_title": "Geometry Theorems PDF",
    "display_filename": "Class10_Maths_Theorems.pdf",
    "file_type": "pdf",
    "mime_type": "application/pdf",
    "file_size": 1048576,
    "bucket_name": "study-materials",
    "storage_path": "materials/10/11111111-1111-1111-1111-111111111111/file_1.pdf",
    "external_url": None,
    "sort_order": 0,
    "download_count": 15,
    "created_at": "2026-11-20T10:00:00Z",
}

SAMPLE_MATERIAL = {
    "id": "11111111-1111-1111-1111-111111111111",
    "title": "Class 10 Geometry Complete Theorems",
    "slug": "class-10-geometry-complete-theorems",
    "description": "Proof of Thales and Pythagoras theorems with solved examples.",
    "class_id": 10,
    "subject_id": 8,
    "category_id": 1,
    "medium": "both",
    "question_formats": ["2_marks", "5_marks"],
    "tags": ["geometry", "theorems", "maths"],
    "academic_year": "2024-2025",
    "author_name": "K. Ramanathan",
    "author_organization": "GHSS Madurai",
    "status": "published",
    "view_count": 120,
    "download_count": 45,
    "created_by": "99999999-9999-9999-9999-999999999999",
    "updated_by": "99999999-9999-9999-9999-999999999999",
    "created_at": "2026-11-20T10:00:00Z",
    "updated_at": "2026-11-20T10:00:00Z",
    "class_name": "Class 10",
    "subject_name": "Mathematics",
    "category_name": "Geometry & Theorems",
    "category_slug": "geometry-theorems",
    "file_count": 1,
    "total_size_bytes": 1048576,
}

SAMPLE_DRAFT = {
    "id": "22222222-2222-2222-2222-222222222222",
    "title": "Class 10 General Study Timetable",
    "slug": "class-10-general-study-timetable",
    "description": "General 100-day schedule",
    "class_id": 10,
    "subject_id": None,
    "category_id": None,
    "medium": "both",
    "question_formats": [],
    "tags": ["timetable", "schedule"],
    "academic_year": "2024-2025",
    "author_name": "Admin Team",
    "author_organization": None,
    "status": "draft",
    "view_count": 0,
    "download_count": 0,
    "created_by": "99999999-9999-9999-9999-999999999999",
    "updated_by": "99999999-9999-9999-9999-999999999999",
    "created_at": "2026-11-20T11:00:00Z",
    "updated_at": "2026-11-20T11:00:00Z",
    "class_name": "Class 10",
    "subject_name": None,
    "category_name": None,
    "category_slug": None,
    "file_count": 0,
    "total_size_bytes": 0,
}


class MockStorageBucket:
    def upload(self, path, file, file_options=None):
        return {"Key": path}

    def download(self, path):
        return b"%PDF-1.4 dummy pdf bytes"

    def remove(self, paths):
        return [{"Key": p} for p in paths]

    def get_public_url(self, path):
        return f"https://example.supabase.co/study-materials/{path}"

    def create_signed_url(self, path, expires_in):
        return {"signedURL": f"https://example.supabase.co/submissions/{path}?token=signed"}


class MockStorageClient:
    def from_(self, bucket):
        return MockStorageBucket()


def _make_mock_db(materials=None, files=None):
    mock_db = MagicMock()
    mats = [dict(m) for m in (materials or [SAMPLE_MATERIAL, SAMPLE_DRAFT])]
    file_list = [dict(f) for f in (files or [SAMPLE_FILE])]
    likes_data = []
    comments_data = []

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        p = params or {}

        # Class lookup
        if "from classes where" in sql or "from classes c" in sql:
            cid = p.get("class_id") or p.get("id")
            if cid in (9, 10, 11, 12):
                return MockResult([{"id": cid, "name": f"Class {cid}", "slug": str(cid)}])
            return MockResult([])

        # Subject lookup
        if "from subjects where" in sql or "from subjects s" in sql:
            sid = p.get("subject_id") or p.get("id")
            if sid == 8:
                return MockResult([{"id": 8, "class_id": 10, "name": "Mathematics", "slug": "maths"}])
            elif sid == 99:
                # Subject belonging to Class 11
                return MockResult([{"id": 99, "class_id": 11, "name": "Physics", "slug": "physics"}])
            return MockResult([])

        # Category lookup
        if "from material_categories" in sql:
            cid = p.get("category_id") or p.get("id")
            if cid == 1:
                return MockResult([{"id": 1, "class_id": None, "subject_id": None, "name": "Global Cat", "slug": "global-cat"}])
            return MockResult([])

        # Files lookup
        if "from material_files" in sql:
            mid = str(p.get("material_id", ""))
            fid = str(p.get("id", "")) or str(p.get("file_id", ""))
            if fid:
                match = next((f for f in file_list if str(f["id"]) == fid), None)
                return MockResult([match] if match else [])
            matches = [f for f in file_list if str(f.get("material_id")) == mid]
            return MockResult(matches)

        # Single material by slug or ID
        if "where sm.slug = :slug" in sql or "where sm.id = :id" in sql:
            slug = p.get("slug")
            mid = str(p.get("id", ""))
            published_only = "sm.status = 'published'" in sql

            match = None
            for m in mats:
                if slug and m["slug"] == slug:
                    match = m
                    break
                if mid and str(m["id"]) == mid:
                    match = m
                    break

            if match:
                if published_only and match["status"] != "published":
                    return MockResult([])
                return MockResult([match])
            return MockResult([])

        # List materials & count
        if "select count(*)::int from study_materials" in sql:
            count = len([m for m in mats if "sm.status = 'published'" not in sql or m["status"] == "published"])
            return MockResult(scalar_val=count)

        if "select sm.id, sm.title" in sql:
            published_only = "sm.status = 'published'" in sql
            res = [m for m in mats if not published_only or m["status"] == "published"]
            return MockResult(res)

        # Insert material
        if "insert into study_materials" in sql:
            import uuid
            new_id = uuid.uuid4()
            new_mat = {
                "id": new_id,
                "title": p.get("title"),
                "slug": p.get("slug"),
                "description": p.get("description"),
                "class_id": p.get("class_id"),
                "subject_id": p.get("subject_id"),
                "category_id": p.get("category_id"),
                "medium": p.get("medium", "both"),
                "question_formats": p.get("question_formats", []),
                "tags": p.get("tags", []),
                "academic_year": p.get("academic_year"),
                "author_name": p.get("author_name"),
                "author_organization": p.get("author_organization"),
                "status": p.get("status", "draft"),
                "view_count": 0,
                "download_count": 0,
                "created_by": p.get("created_by"),
                "updated_by": p.get("created_by"),
                "created_at": "2026-11-20T12:00:00Z",
                "updated_at": "2026-11-20T12:00:00Z",
                "class_name": "Class 10",
                "subject_name": "Mathematics" if p.get("subject_id") else None,
                "category_name": "Category 1" if p.get("category_id") else None,
                "category_slug": "cat-1" if p.get("category_id") else None,
                "file_count": 0,
                "total_size_bytes": 0,
            }
            mats.append(new_mat)
            return MockResult([new_mat])

        # Insert file
        if "insert into material_files" in sql:
            import uuid
            new_fid = uuid.uuid4()
            new_f = {
                "id": new_fid,
                "material_id": p.get("material_id"),
                "file_title": p.get("file_title"),
                "display_filename": p.get("display_filename"),
                "file_type": p.get("file_type", "pdf"),
                "mime_type": p.get("mime_type"),
                "file_size": p.get("file_size", 0),
                "bucket_name": p.get("bucket_name"),
                "storage_path": p.get("storage_path"),
                "external_url": p.get("external_url"),
                "sort_order": p.get("sort_order", 0),
                "download_count": 0,
                "created_at": "2026-11-20T12:00:00Z",
            }
            file_list.append(new_f)
            return MockResult([new_f])

        # Update status
        if "update study_materials" in sql:
            mid = str(p.get("id", ""))
            match = next((m for m in mats if str(m["id"]) == mid), None)
            if match:
                if "status" in p: match["status"] = p["status"]
                if "title" in p: match["title"] = p["title"]
                return MockResult([match])
            return MockResult([])

        # Delete material
        if "delete from study_materials" in sql:
            mid = str(p.get("id", ""))
            mats[:] = [m for m in mats if str(m["id"]) != mid]
            return MockResult([{"id": mid}])

        # Delete file
        if "delete from material_files" in sql:
            fid = str(p.get("id", ""))
            file_list[:] = [f for f in file_list if str(f["id"]) != fid]
            return MockResult([{"id": fid}])

        # Likes mutations & lookup
        if "insert into study_material_likes" in sql:
            likes_data.append({"material_id": str(p.get("material_id")), "firebase_uid": p.get("firebase_uid")})
            return MockResult([])

        if "delete from study_material_likes" in sql:
            mid = str(p.get("material_id"))
            fuid = p.get("firebase_uid")
            likes_data[:] = [l for l in likes_data if not (l["material_id"] == mid and l["firebase_uid"] == fuid)]
            return MockResult([])

        if "from study_material_likes" in sql:
            mid = str(p.get("material_id", ""))
            fuid = p.get("firebase_uid")
            if "count(*)::int" in sql:
                cnt = len([l for l in likes_data if l["material_id"] == mid])
                return MockResult(scalar_val=cnt)
            match = next((l for l in likes_data if l["material_id"] == mid and l["firebase_uid"] == fuid), None)
            return MockResult([match] if match else [])

        # Comments mutations & lookup
        if "insert into study_material_comments" in sql:
            import uuid
            new_cid = str(uuid.uuid4())
            now_dt = datetime.now(timezone.utc)
            new_c = {
                "id": new_cid,
                "material_id": str(p.get("material_id")),
                "firebase_uid": p.get("firebase_uid"),
                "author_name": p.get("author_name"),
                "author_avatar": p.get("author_avatar"),
                "parent_id": str(p.get("parent_id")) if p.get("parent_id") else None,
                "content": p.get("content"),
                "is_deleted": False,
                "created_at": now_dt,
                "updated_at": now_dt,
            }
            comments_data.append(new_c)
            return MockResult([new_c])

        if "update study_material_comments" in sql:
            cid = str(p.get("comment_id", ""))
            match = next((c for c in comments_data if str(c["id"]) == cid), None)
            if match:
                match["is_deleted"] = True
                return MockResult(rowcount=1)
            return MockResult(rowcount=0)

        if "delete from study_material_comments" in sql:
            cid = str(p.get("comment_id", ""))
            comments_data[:] = [c for c in comments_data if str(c["id"]) != cid]
            return MockResult(rowcount=1)

        if "from study_material_comments" in sql:
            if "where id::text = :cid" in sql or "where id::text = :comment_id" in sql:
                cid = str(p.get("cid") or p.get("comment_id", ""))
                match = next((c for c in comments_data if str(c["id"]) == cid), None)
                return MockResult([match] if match else [])
            mid = str(p.get("material_id", ""))
            matches = [c for c in comments_data if c["material_id"] == mid and not c.get("is_deleted")]
            return MockResult(matches)

        return MockResult([])

    mock_db.execute.side_effect = execute_handler
    return mock_db


@pytest.fixture
def mock_user():
    return {
        "id": "88888888-8888-8888-8888-888888888888",
        "firebase_uid": "user_uid_123",
        "email": "student@hungrylearner.com",
        "display_name": "Student User",
        "role": "CONTRIBUTOR",
        "is_active": True,
    }


@pytest.fixture
def mock_admin():
    return {
        "id": "99999999-9999-9999-9999-999999999999",
        "firebase_uid": "admin_uid_123",
        "email": "admin@hungrylearner.com",
        "role": "ADMIN",
        "is_active": True,
    }


@pytest.fixture
def mock_super_admin():
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "firebase_uid": "superadmin_uid_123",
        "email": "superadmin@hungrylearner.com",
        "role": "SUPER_ADMIN",
        "is_active": True,
    }


# ── Public Endpoints Tests ────────────────────────────────────────────────────

def test_public_list_materials_only_published():
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.get("/api/v1/study-materials")
        assert res.status_code == 200
        data = res.json()
        assert "data" in data
        # Drafts must NOT appear in public listing
        for item in data["data"]:
            assert item["status"] == "published"
    finally:
        app.dependency_overrides.clear()


def test_public_get_material_by_slug():
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.get("/api/v1/study-materials/class-10-geometry-complete-theorems")
        assert res.status_code == 200
        data = res.json()
        assert data["slug"] == "class-10-geometry-complete-theorems"
        assert len(data["files"]) == 1
        assert data["files"][0]["file_title"] == "Geometry Theorems PDF"
    finally:
        app.dependency_overrides.clear()


def test_public_cannot_view_draft_by_slug():
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        # Requesting a draft slug anonymously should return 404
        res = client.get("/api/v1/study-materials/class-10-general-study-timetable")
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_track_download():
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.post(
            f"/api/v1/study-materials/{SAMPLE_MATERIAL['id']}/files/{SAMPLE_FILE['id']}/download"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "download_url" in data
    finally:
        app.dependency_overrides.clear()


# ── Admin Creation & Validation Tests ─────────────────────────────────────────

def test_admin_create_class_level_material(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        payload = {
            "title": "Class 10 General Exam Strategy Guide",
            "class_id": 10,
            "subject_id": None,  # Class-level general material
            "category_id": None,
            "medium": "both",
            "question_formats": [],
            "tags": ["strategy", "exam-prep"],
            "academic_year": "2024-2025",
            "status": "draft",
            "files": [
                {
                    "file_title": "Video Walkthrough",
                    "display_filename": "Video Walkthrough",
                    "file_type": "video",
                    "external_url": "https://youtube.com/watch?v=12345",
                }
            ],
        }

        # Multi-part upload
        res = client.post(
            "/api/v1/admin/study-materials",
            data={"payload": json.dumps(payload)},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["class_id"] == 10
        assert data["subject_id"] is None
        assert data["status"] == "draft"
    finally:
        app.dependency_overrides.clear()


def test_reject_mismatched_subject_and_class(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        # Subject 99 belongs to Class 11, but class_id 10 is passed
        payload = {
            "title": "Mismatched Subject Material",
            "class_id": 10,
            "subject_id": 99,
            "medium": "both",
            "status": "draft",
            "files": [],
        }
        res = client.post(
            "/api/v1/admin/study-materials",
            data={"payload": json.dumps(payload)},
        )
        assert res.status_code == 422
        assert "does not belong to class" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_admin_upload_with_binary_pdf(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        payload = {
            "title": "Maths Unit 1 Notes",
            "class_id": 10,
            "subject_id": 8,
            "medium": "tamil",
            "status": "draft",
            "files": [],
        }
        # Fake PDF content with valid %PDF- magic bytes
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = [("files", ("unit1_notes.pdf", io.BytesIO(pdf_bytes), "application/pdf"))]

        res = client.post(
            "/api/v1/admin/study-materials",
            data={"payload": json.dumps(payload)},
            files=files,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Maths Unit 1 Notes"
    finally:
        app.dependency_overrides.clear()


def test_reject_spoofed_file_magic_bytes(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        payload = {
            "title": "Malicious Upload Attempt",
            "class_id": 10,
            "subject_id": 8,
            "status": "draft",
            "files": [],
        }
        # HTML disguised as PDF
        fake_pdf = b"<html><script>alert(1)</script></html>"
        files = [("files", ("virus.pdf", io.BytesIO(fake_pdf), "application/pdf"))]

        res = client.post(
            "/api/v1/admin/study-materials",
            data={"payload": json.dumps(payload)},
            files=files,
        )
        assert res.status_code == 400
        assert "does not match expected binary format" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── Lifecycle & Role Security Tests ───────────────────────────────────────────

def test_admin_update_status_published_and_archived(mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: mock_admin
    try:
        # Archive published material
        res = client.patch(
            f"/api/v1/admin/study-materials/{SAMPLE_MATERIAL['id']}/status",
            json={"status": "archived"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "archived"

        # Restore archived material
        res2 = client.patch(
            f"/api/v1/admin/study-materials/{SAMPLE_MATERIAL['id']}/status",
            json={"status": "published"},
        )
        assert res2.status_code == 200
        assert res2.json()["status"] == "published"
    finally:
        app.dependency_overrides.clear()


def test_superadmin_permanent_deletion(mock_super_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: mock_super_admin
    try:
        res = client.delete(f"/api/v1/admin/study-materials/{SAMPLE_MATERIAL['id']}")
        assert res.status_code == 200
        data = res.json()
        assert data["deleted"] is True
    finally:
        app.dependency_overrides.clear()


def test_non_admin_cannot_delete():
    client = TestClient(app)
    # No auth override -> 401 unauthorized
    res = client.delete(f"/api/v1/admin/study-materials/{SAMPLE_MATERIAL['id']}")
    assert res.status_code == 401


# ── Study Material Likes & Comments Tests ─────────────────────────────────────

def test_study_material_toggle_like(mock_user):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mat_id = SAMPLE_MATERIAL["id"]
    try:
        # First like: should increment count to 1 and has_liked = True
        res = client.post(f"/api/v1/study-materials/{mat_id}/like")
        assert res.status_code == 200
        data = res.json()
        assert data["material_id"] == mat_id
        assert data["has_liked"] is True
        assert data["likes_count"] == 1

        # Second like: should toggle off, count to 0 and has_liked = False
        res2 = client.post(f"/api/v1/study-materials/{mat_id}/like")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["has_liked"] is False
        assert data2["likes_count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_study_material_get_likes_public_and_authenticated(mock_user):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    mat_id = SAMPLE_MATERIAL["id"]
    try:
        # Public anonymous access: has_liked = False, likes_count = 0
        res = client.get(f"/api/v1/study-materials/{mat_id}/likes")
        assert res.status_code == 200
        data = res.json()
        assert data["likes_count"] == 0
        assert data["has_liked"] is False

        # Authenticate and like
        app.dependency_overrides[get_current_user] = lambda: mock_user
        res_like = client.post(f"/api/v1/study-materials/{mat_id}/like")
        assert res_like.status_code == 200

        # Check likes with current_user_optional set
        app.dependency_overrides[get_current_user_optional] = lambda: mock_user
        res_auth = client.get(f"/api/v1/study-materials/{mat_id}/likes")
        assert res_auth.status_code == 200
        auth_data = res_auth.json()
        assert auth_data["likes_count"] == 1
        assert auth_data["has_liked"] is True
    finally:
        app.dependency_overrides.clear()


def test_study_material_comments_thread_and_reply(mock_user):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mat_id = SAMPLE_MATERIAL["id"]
    try:
        # Add root comment
        comment_payload = {
            "content": "Excellent theorems summary, very helpful!",
            "author_avatar": "https://example.com/avatar.jpg",
        }
        res = client.post(f"/api/v1/study-materials/{mat_id}/comments", json=comment_payload)
        assert res.status_code == 201
        root_comment = res.json()
        assert root_comment["content"] == comment_payload["content"]
        assert root_comment["author_name"] == mock_user["display_name"]
        root_id = root_comment["id"]

        # Add reply to root comment
        reply_payload = {
            "content": "Agreed, Pythagoras theorem proof is very clear.",
            "parent_id": root_id,
        }
        res_reply = client.post(f"/api/v1/study-materials/{mat_id}/comments", json=reply_payload)
        assert res_reply.status_code == 201
        reply_comment = res_reply.json()
        assert reply_comment["parent_id"] == root_id

        # Get comments list - public endpoint
        res_list = client.get(f"/api/v1/study-materials/{mat_id}/comments")
        assert res_list.status_code == 200
        comments_tree = res_list.json()
        assert len(comments_tree) == 1
        assert comments_tree[0]["id"] == root_id
        assert len(comments_tree[0]["replies"]) == 1
        assert comments_tree[0]["replies"][0]["id"] == reply_comment["id"]
    finally:
        app.dependency_overrides.clear()


def test_study_material_comment_deletion_owner_and_admin(mock_user, mock_admin):
    client = TestClient(app)
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_user
    mat_id = SAMPLE_MATERIAL["id"]
    try:
        # User creates comment
        res = client.post(f"/api/v1/study-materials/{mat_id}/comments", json={"content": "Comment to delete"})
        assert res.status_code == 201
        cid = res.json()["id"]

        # Another unauthorized user cannot delete it
        other_user = {
            "id": "77777777-7777-7777-7777-777777777777",
            "firebase_uid": "other_uid_456",
            "email": "other@hungrylearner.com",
            "role": "CONTRIBUTOR",
            "is_active": True,
        }
        app.dependency_overrides[get_current_user] = lambda: other_user
        res_del_forbidden = client.delete(f"/api/v1/study-materials/comments/{cid}")
        assert res_del_forbidden.status_code == 403

        # Original owner can delete it
        app.dependency_overrides[get_current_user] = lambda: mock_user
        res_del_owner = client.delete(f"/api/v1/study-materials/comments/{cid}")
        assert res_del_owner.status_code == 200
        assert res_del_owner.json()["deleted"] is True

        # Create another comment and let admin delete it
        res2 = client.post(f"/api/v1/study-materials/{mat_id}/comments", json={"content": "Admin delete test"})
        assert res2.status_code == 201
        cid2 = res2.json()["id"]

        app.dependency_overrides[get_current_user] = lambda: mock_admin
        res_del_admin = client.delete(f"/api/v1/study-materials/comments/{cid2}")
        assert res_del_admin.status_code == 200
        assert res_del_admin.json()["deleted"] is True
    finally:
        app.dependency_overrides.clear()

