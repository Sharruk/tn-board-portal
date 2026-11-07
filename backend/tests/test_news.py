"""
Tests for News & Updates endpoints and service:
  - GET    /api/v1/news
  - GET    /api/v1/news/{id}
  - POST   /api/v1/news (Admin)
  - PATCH  /api/v1/news/{id} (Admin)
  - DELETE /api/v1/news/{id} (Admin)
  - Centralized audit logging and transactional outbox side-effects
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.main import app
from app.repositories.news_repository import NewsRepository
from app.services.news_service import NewsService


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

SAMPLE_NEWS = {
    "id": "11111111-2222-3333-4444-555555555555",
    "title": "TN Board 10th Result Date Announced",
    "slug": "tn-board-10th-result-date-announced",
    "category": "Result Announcements",
    "summary": "State education board announces dates for Class 10 results.",
    "content": "Official announcement has confirmed the date...",
    "tags": ["results", "10th", "sslc"],
    "thumbnail_url": "https://example.supabase.co/news-media/thumb1.jpg",
    "thumbnail_alt": "Result press meet",
    "youtube_url": None,
    "pdf_url": "https://example.supabase.co/news-media/press_release.pdf",
    "class_id": 10,
    "district": None,
    "status": "published",
    "is_pinned": True,
    "views": 150,
    "published_at": _NOW,
    "created_at": _NOW,
    "updated_at": _NOW,
    "class_name": "Class 10",
}


def _make_mock_db(news_data=None):
    mock_db = MagicMock()
    article = dict(news_data or SAMPLE_NEWS)

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=1)
        if "from news_updates" in sql and ("where id" in sql or "slug = :slug" in sql):
            return MockResult([article])
        if "from news_updates" in sql:
            return MockResult([article])
        if "insert into news_updates" in sql:
            return MockResult([article])
        if "update news_updates" in sql:
            return MockResult([article])
        if "delete from news_updates" in sql:
            return MockResult(rowcount=1)
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "activity-mock-1", "metadata": "{}"}])
        if "storage_outbox" in sql:
            return MockResult([{"id": "outbox-mock-1"}])
        return MockResult([])

    mock_db.execute.side_effect = execute_handler
    return mock_db


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_list_news_public():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/news?category=Result+Announcements")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["title"] == "TN Board 10th Result Date Announced"
    finally:
        app.dependency_overrides.clear()


def test_get_news_public():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/news/11111111-2222-3333-4444-555555555555")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "11111111-2222-3333-4444-555555555555"
        assert data["slug"] == "tn-board-10th-result-date-announced"
    finally:
        app.dependency_overrides.clear()


def test_create_news_admin_success():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "ADMIN",
        "display_name": "Admin User",
    }

    payload = {
        "title": "TN Board 10th Result Date Announced",
        "category": "Result Announcements",
        "summary": "State education board announces dates for Class 10 results.",
        "content": "Official announcement has confirmed the date...",
        "tags": ["results", "10th"],
        "class_id": 10,
        "status": "published",
        "is_pinned": True,
    }

    try:
        client = TestClient(app)
        resp = client.post("/api/v1/news", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "TN Board 10th Result Date Announced"
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_create_news_unauthorized():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "title": "Unauthorized News",
        "category": "Result Announcements",
        "content": "Content...",
    }

    try:
        client = TestClient(app)
        resp = client.post("/api/v1/news", json=payload)
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


def test_update_news_admin_success():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.patch(
            "/api/v1/news/11111111-2222-3333-4444-555555555555",
            json={"is_pinned": False},
        )
        assert resp.status_code == 200
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_delete_news_admin_success():
    mock_db = _make_mock_db()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.delete("/api/v1/news/11111111-2222-3333-4444-555555555555")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert data["storage_deleted"] is True
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_audit_failure_rolls_back_news_creation():
    mock_db = MagicMock()
    article = dict(SAMPLE_NEWS)

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into news_updates" in sql:
            return MockResult([article])
        if "admin_activity_logs" in sql:
            raise RuntimeError("Database error during audit insert")
        return MockResult([])

    mock_db.execute.side_effect = execute_handler

    service = NewsService(mock_db)
    from app.schemas.news import NewsCreate
    req = NewsCreate(
        title="Test News",
        category="General",
        content="Content body...",
    )

    with pytest.raises(RuntimeError, match="Database error during audit insert"):
        service.create_news(
            req=req,
            current_user={"user_id": "admin-1", "email": "admin@example.com", "role": "ADMIN"},
        )

    assert mock_db.rollback.called
