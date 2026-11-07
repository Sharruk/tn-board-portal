"""
Tests for Official Notices endpoints and service:
  - GET    /api/v1/notices
  - GET    /api/v1/notices/{id}
  - POST   /api/v1/notices (Admin)
  - PATCH  /api/v1/notices/{id} (Admin)
  - DELETE /api/v1/notices/{id} (Admin)
  - Transactional audit logging and outbox side-effects
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.main import app
from app.repositories.notices_repository import NoticesRepository
from app.services.notices_service import NoticesService


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


_NOW = datetime.now(timezone.utc)

SAMPLE_NOTICE = {
    "id": 101,
    "title": "Quarterly Exam Time Table 2024",
    "category": "Exam Updates",
    "class_id": 10,
    "year": 2024,
    "description": "Official schedule for Class 10 quarterly exams.",
    "file_path": "quarterly-exam-2024.pdf",
    "public_url": "https://example.supabase.co/official-updates/quarterly-exam-2024.pdf",
    "file_type": "pdf",
    "youtube_url": None,
    "is_visible": True,
    "is_pinned": False,
    "expires_at": None,
    "view_count": 45,
    "download_count": 12,
    "created_at": _NOW,
    "updated_at": _NOW,
    "class_name": "Class 10",
}


def _make_mock_db(notice_data=None):
    mock_db = MagicMock()
    notice = dict(notice_data or SAMPLE_NOTICE)

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=1)
        if "from official_notices" in sql and "where id" in sql:
            return MockResult([notice])
        if "from official_notices" in sql:
            return MockResult([notice])
        if "insert into official_notices" in sql:
            return MockResult([notice])
        if "update official_notices" in sql:
            return MockResult([notice])
        if "delete from official_notices" in sql:
            return MockResult(rowcount=1)
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "activity-mock-1", "metadata": "{}"}])
        if "storage_outbox" in sql:
            return MockResult([{"id": "outbox-mock-1"}])
        return MockResult([])

    mock_db.execute.side_effect = execute_handler
    return mock_db


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_list_notices_public():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/notices?category=Exam+Updates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "Quarterly Exam Time Table 2024"
    finally:
        app.dependency_overrides.clear()


def test_get_notice_public():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/notices/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 101
        assert data["category"] == "Exam Updates"
    finally:
        app.dependency_overrides.clear()


def test_create_notice_admin_success():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "ADMIN",
        "display_name": "Admin User",
    }

    payload = {
        "title": "Quarterly Exam Time Table 2024",
        "category": "Exam Updates",
        "class_id": 10,
        "year": 2024,
        "description": "Official schedule for Class 10 quarterly exams.",
        "file_path": "quarterly-exam-2024.pdf",
        "public_url": "https://example.supabase.co/official-updates/quarterly-exam-2024.pdf",
        "file_type": "pdf",
        "is_visible": True,
        "is_pinned": False,
    }

    try:
        client = TestClient(app)
        resp = client.post("/api/v1/notices", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == 101
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_create_notice_unauthorized():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "title": "Unauthorized Notice",
        "category": "Exam Updates",
        "year": 2024,
    }

    try:
        client = TestClient(app)
        resp = client.post("/api/v1/notices", json=payload)
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


def test_update_notice_admin_success():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.patch("/api/v1/notices/101", json={"is_pinned": True})
        assert resp.status_code == 200
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_delete_notice_admin_success():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.delete("/api/v1/notices/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert data["storage_deleted"] is True
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_audit_failure_rolls_back_notice_creation():
    mock_db = MagicMock()
    notice = dict(SAMPLE_NOTICE)

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into official_notices" in sql:
            return MockResult([notice])
        if "admin_activity_logs" in sql:
            raise RuntimeError("Database error during audit insert")
        return MockResult([])

    mock_db.execute.side_effect = execute_handler

    service = NoticesService(mock_db)
    from app.schemas.notice import NoticeCreate
    req = NoticeCreate(
        title="Test Notice",
        category="General",
        year=2024,
    )

    with pytest.raises(RuntimeError, match="Database error during audit insert"):
        service.create_notice(
            req=req,
            current_user={"user_id": "admin-1", "email": "admin@example.com", "role": "ADMIN"},
        )

    assert mock_db.rollback.called
