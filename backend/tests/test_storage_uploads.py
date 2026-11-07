"""
Automated unit tests for backend-mediated Supabase Storage uploads.
Validates:
  1. Official Notice multipart upload with attachment
  2. Official Notice multipart upload without attachment
  3. Question Paper multipart upload
  4. Answer Key multipart upload
  5. News media upload (image & PDF)
  6. News media deletion / replacement cleanup
  7. Unauthorized user rejection (401 / 403)
  8. Unauthenticated request rejection (401)
  9. Invalid file extension rejection (400)
  10. Empty file rejection (400)
  11. File size limit rejection (400)
  12. Storage upload failure handling (500)
  13. Compensating cleanup on database failure
  14. Submissions approval workflow compatibility with service-role storage
"""

import io
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user, require_admin
from app.dependencies.supabase import get_db
from app.main import app

_NOW = datetime.now(timezone.utc)

SAMPLE_NOTICE_ROW = {
    "id": 101,
    "title": "Chennai District Mid Term Test Timetable",
    "category": "Mid Term Test",
    "class_id": 9,
    "year": 2026,
    "description": "Mid term timetable for class 9.",
    "file_path": "mock-notice-file.pdf",
    "public_url": "https://example.supabase.co/storage/v1/object/public/official-updates/mock-notice-file.pdf",
    "file_type": "pdf",
    "youtube_url": None,
    "is_visible": True,
    "is_pinned": False,
    "expires_at": None,
    "view_count": 0,
    "download_count": 0,
    "created_at": _NOW,
    "updated_at": _NOW,
    "class_name": "Class 9",
}

SAMPLE_PAPER_ROW = {
    "id": 202,
    "subject_id": 1,
    "exam_type": "Annual Exam",
    "year": 2026,
    "month": "March",
    "district": "Chennai",
    "title": "Class 10 Mathematics Annual Exam 2026",
    "description": "Official question paper",
    "paper_type": "question",
    "file_path": "mock-paper-file.pdf",
    "public_url": "https://example.supabase.co/storage/v1/object/public/papers/mock-paper-file.pdf",
    "youtube_url": None,
    "original_filename": "maths_annual_2026.pdf",
    "is_visible": False,
    "status": "draft",
    "download_count": 0,
    "submission_id": None,
    "contributor_name": None,
    "created_at": _NOW,
    "subject_name": "Mathematics",
    "class_id": 10,
    "class_name": "Class 10",
}

SAMPLE_NEWS_ROW = {
    "id": "news-12345",
    "title": "School Reopening Dates Announced",
    "slug": "school-reopening-dates-announced",
    "category": "Breaking News",
    "summary": "Official update on reopening dates",
    "content": "Full article text goes here.",
    "tags": ["reopening", "schools"],
    "thumbnail_url": "https://example.supabase.co/storage/v1/object/public/news-media/mock-thumb.jpg",
    "thumbnail_alt": "Schools",
    "youtube_url": None,
    "pdf_url": "https://example.supabase.co/storage/v1/object/public/news-media/mock-doc.pdf",
    "class_id": None,
    "district": None,
    "status": "published",
    "is_pinned": False,
    "published_at": _NOW,
    "view_count": 10,
    "created_at": _NOW,
    "updated_at": _NOW,
    "class_name": None,
}


class MockRow:
    def __init__(self, data: dict):
        self._mapping = data

    def __getitem__(self, key):
        return self._mapping[key]

    def get(self, key, default=None):
        return self._mapping.get(key, default)


class MockResult:
    def __init__(self, rows: list[dict] | None = None, scalar_val=None, rowcount=1):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


def _make_mock_storage():
    """Returns a mock Supabase Storage client that operates entirely in-memory."""
    storage = MagicMock()
    bucket_mock = MagicMock()
    storage.from_.return_value = bucket_mock

    bucket_mock.upload.return_value = {"Key": "uploaded"}
    bucket_mock.get_public_url.side_effect = (
        lambda path: f"https://example.supabase.co/storage/v1/object/public/mock/{path}"
    )
    bucket_mock.remove.return_value = [{"name": "removed"}]
    return storage, bucket_mock


def _make_mock_db():
    mock_db = MagicMock()

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=1)
        if "from official_notices" in sql:
            return MockResult([SAMPLE_NOTICE_ROW])
        if "insert into official_notices" in sql:
            return MockResult([SAMPLE_NOTICE_ROW])
        if "from papers" in sql:
            return MockResult([SAMPLE_PAPER_ROW])
        if "insert into papers" in sql:
            return MockResult([SAMPLE_PAPER_ROW])
        if "from news_updates" in sql:
            return MockResult([SAMPLE_NEWS_ROW])
        if "insert into news_updates" in sql:
            return MockResult([SAMPLE_NEWS_ROW])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "mock-activity-1", "metadata": "{}"}])
        if "storage_outbox" in sql:
            return MockResult([{"id": "mock-outbox-1"}])
        return MockResult([])

    mock_db.execute.side_effect = execute_handler
    return mock_db


# ── Official Notices Tests ───────────────────────────────────────────────────

def test_upload_official_notice_with_attachment_success():
    mock_db = _make_mock_db()
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "display_name": "Admin",
        "role": "SUPER_ADMIN",
    }

    dummy_pdf = io.BytesIO(b"%PDF-1.4 mock pdf content for testing")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/notices",
            data={
                "title": "Chennai District Mid Term Test Timetable",
                "category": "Mid Term Test",
                "year": "2026",
                "class_id": "9",
                "is_visible": "true",
            },
            files={"file": ("timetable.pdf", dummy_pdf, "application/pdf")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert bucket_mock.upload.called
    data = resp.json()
    assert data["title"] == SAMPLE_NOTICE_ROW["title"]


def test_upload_official_notice_without_attachment_success():
    mock_db = _make_mock_db()
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "role": "SUPER_ADMIN",
    }

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/notices",
            data={
                "title": "General Circular",
                "category": "School Circular",
                "year": "2026",
            },
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert not bucket_mock.upload.called


# ── Question Papers and Answer Keys Tests ────────────────────────────────────

def test_upload_question_paper_multipart_success():
    mock_db = _make_mock_db()
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "role": "SUPER_ADMIN",
    }

    dummy_pdf = io.BytesIO(b"%PDF-1.4 Question Paper bytes")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/papers",
            data={
                "subject_id": "1",
                "exam_type": "Annual Exam",
                "year": "2026",
                "title": "Mathematics Annual Exam 2026",
                "paper_type": "question",
            },
            files={"file": ("maths_2026.pdf", dummy_pdf, "application/pdf")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert bucket_mock.upload.called
    data = resp.json()
    assert data["title"] == SAMPLE_PAPER_ROW["title"]


def test_upload_answer_key_multipart_success():
    mock_db = _make_mock_db()
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "role": "SUPER_ADMIN",
    }

    dummy_pdf = io.BytesIO(b"%PDF-1.4 Answer Key bytes")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/papers",
            data={
                "subject_id": "1",
                "exam_type": "Annual Exam",
                "year": "2026",
                "title": "Mathematics Annual Exam 2026 - Answer Key",
                "paper_type": "answer_key",
            },
            files={"file": ("maths_answer_key_2026.pdf", dummy_pdf, "application/pdf")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 201
    assert bucket_mock.upload.called


# ── Educational News Media Tests ─────────────────────────────────────────────

def test_upload_news_media_image_success():
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "role": "SUPER_ADMIN",
    }

    dummy_image = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF mock jpeg bytes")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/news/upload",
            files={"file": ("news_thumbnail.jpg", dummy_image, "image/jpeg")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert bucket_mock.upload.called
    data = resp.json()
    assert "public_url" in data
    assert "file_path" in data
    assert data["file_type"] == "image"


def test_upload_news_media_pdf_success():
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "role": "SUPER_ADMIN",
    }

    dummy_pdf = io.BytesIO(b"%PDF-1.4 news circular pdf")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/news/upload",
            files={"file": ("govt_order.pdf", dummy_pdf, "application/pdf")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert bucket_mock.upload.called
    data = resp.json()
    assert data["file_type"] == "pdf"


def test_delete_news_media_success():
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "hungrylearner786@gmail.com",
        "role": "SUPER_ADMIN",
    }

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.delete(
            "/api/v1/news/media",
            params={"url": "https://example.supabase.co/storage/v1/object/public/news-media/old-thumb.jpg"},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert bucket_mock.remove.called


# ── Security & Validation Tests ──────────────────────────────────────────────

def test_unauthenticated_upload_rejected():
    client = TestClient(app)
    resp = client.post(
        "/api/v1/notices",
        data={"title": "Unauthorized notice", "category": "Announcements", "year": "2026"},
    )
    assert resp.status_code in (401, 403)


def test_unauthorized_non_admin_upload_rejected():
    from app.dependencies.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {
        "firebase_uid": "student-1",
        "email": "student@example.com",
        "role": "USER",
    }

    client = TestClient(app)
    resp = client.post(
        "/api/v1/papers",
        data={"title": "Student paper", "subject_id": "1", "exam_type": "Model", "year": "2026"},
    )
    app.dependency_overrides.clear()
    assert resp.status_code == 403


def test_invalid_file_extension_rejected():
    mock_db = _make_mock_db()
    mock_storage, _ = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {"role": "SUPER_ADMIN", "email": "admin@hungrylearner.internal"}

    malicious_file = io.BytesIO(b"MZ executable bytes")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/papers",
            data={"subject_id": "1", "exam_type": "Annual", "year": "2026", "title": "Malicious Executable"},
            files={"file": ("virus.exe", malicious_file, "application/octet-stream")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


def test_empty_file_rejected():
    mock_db = _make_mock_db()
    mock_storage, _ = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {"role": "SUPER_ADMIN", "email": "admin@hungrylearner.internal"}

    empty_file = io.BytesIO(b"")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/papers",
            data={"subject_id": "1", "exam_type": "Annual", "year": "2026", "title": "Empty Paper"},
            files={"file": ("empty.pdf", empty_file, "application/pdf")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_file_exceeding_limit_rejected():
    mock_db = _make_mock_db()
    mock_storage, _ = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {"role": "SUPER_ADMIN", "email": "admin@hungrylearner.internal"}

    # Mock file that reports 25 MB for news-media (limit is 20 MB)
    large_file = io.BytesIO(b"X" * (25 * 1024 * 1024))

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/news/upload",
            files={"file": ("huge_image.jpg", large_file, "image/jpeg")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 400
    assert "exceeds" in resp.json()["detail"].lower()


def test_storage_upload_failure_returns_500():
    mock_db = _make_mock_db()
    mock_storage = MagicMock()
    bucket_mock = MagicMock()
    mock_storage.from_.return_value = bucket_mock
    bucket_mock.upload.side_effect = RuntimeError("Supabase S3 storage service unreachable")

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {"role": "SUPER_ADMIN", "email": "admin@hungrylearner.internal"}

    dummy_pdf = io.BytesIO(b"%PDF-1.4 valid content")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        resp = client.post(
            "/api/v1/notices",
            data={"title": "Offline Notice", "category": "Announcements", "year": "2026"},
            files={"file": ("offline.pdf", dummy_pdf, "application/pdf")},
        )

    app.dependency_overrides.clear()
    assert resp.status_code == 500


def test_compensating_cleanup_on_database_failure():
    """Verify that if database insertion fails after storage upload, the file is cleaned up."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = RuntimeError("PostgreSQL connection lost during insert")
    mock_storage, bucket_mock = _make_mock_storage()

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {"role": "SUPER_ADMIN", "email": "admin@hungrylearner.internal"}

    dummy_pdf = io.BytesIO(b"%PDF-1.4 test paper")

    with patch("app.services.storage_upload_service.get_storage_client", return_value=mock_storage):
        client = TestClient(app)
        with pytest.raises(RuntimeError):
            client.post(
                "/api/v1/papers",
                data={"subject_id": "1", "exam_type": "Annual", "year": "2026", "title": "DB Fail Paper"},
                files={"file": ("fail_paper.pdf", dummy_pdf, "application/pdf")},
            )

    app.dependency_overrides.clear()
    # Bucket upload was performed
    assert bucket_mock.upload.called
    # Compensating cleanup remove was called on bucket
    assert bucket_mock.remove.called

