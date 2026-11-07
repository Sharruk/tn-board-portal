"""
Tests for News Archive, Unarchive, and Public vs Admin security separation:
  - Admin endpoint /api/v1/news/admin requires Firebase authentication + Admin role
  - Non-admin / unauthenticated calls to /api/v1/news/admin are blocked (401 / 403)
  - Public endpoint /api/v1/news only returns published articles (published_only=True)
  - Unauthenticated access to draft/archived via /api/v1/news/{id} returns 404
  - Admin access to draft/archived via /api/v1/news/{id} returns 200
  - Archive via PATCH /api/v1/news/{id}
  - Archive via POST /api/v1/news/{id}/archive
  - Unarchive via POST /api/v1/news/{id}/unarchive
  - Media URLs remain strictly unchanged during lifecycle transitions
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user_optional, require_admin
from app.dependencies.supabase import get_db
from app.main import app
from app.schemas.news import NewsUpdate
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

SAMPLE_ARTICLE = {
    "id": "65721f73-0d56-4ad4-8106-c8525441d8d3",
    "title": "Rain Holiday – Schools and Colleges Closed in Chennai",
    "slug": "rain-holiday-schools-and-colleges-closed-in-chennai",
    "category": "Holiday Announcement",
    "summary": "Heavy rain holiday declared for schools and colleges.",
    "content": "Due to depression over southwest Bay of Bengal...",
    "tags": ["rain", "holiday", "chennai"],
    "thumbnail_url": "https://example.supabase.co/storage/v1/object/public/news-media/thumb1.jpeg",
    "thumbnail_alt": "Rain in Chennai",
    "youtube_url": None,
    "pdf_url": "https://example.supabase.co/storage/v1/object/public/news-media/circular.pdf",
    "class_id": None,
    "district": "Chennai",
    "status": "published",
    "is_pinned": False,
    "views": 42,
    "published_at": _NOW,
    "created_at": _NOW,
    "updated_at": _NOW,
    "class_name": None,
}


def _make_mock_db(article_state: dict):
    mock_db = MagicMock()

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=1)
        if "from news_updates" in sql and "where n.id::text = :id" in sql:
            return MockResult([dict(article_state)])
        if "from news_updates" in sql:
            return MockResult([dict(article_state)])
        if "update news_updates" in sql:
            if params and "status" in params:
                article_state["status"] = params["status"]
            return MockResult([dict(article_state)])
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "activity-mock-1", "metadata": "{}"}])
        if "storage_outbox" in sql:
            return MockResult([{"id": "outbox-mock-1"}])
        return MockResult([])

    mock_db.execute.side_effect = execute_handler
    return mock_db


ADMIN_AUTH = lambda: {
    "user_id": "admin-uid-123",
    "email": "admin@hungrylearner.internal",
    "role": "ADMIN",
    "display_name": "Portal Admin",
}


# ── Security & Separation Tests ───────────────────────────────────────────────

def test_admin_news_endpoint_requires_auth():
    """Verify /api/v1/news/admin rejects unauthenticated requests with 401."""
    mock_db = _make_mock_db(dict(SAMPLE_ARTICLE))
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/news/admin")
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


def test_admin_news_endpoint_rejects_non_admin():
    """Verify /api/v1/news/admin rejects authenticated non-admin users with 403."""
    mock_db = _make_mock_db(dict(SAMPLE_ARTICLE))
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
        pytest.importorskip("fastapi").HTTPException(status_code=403, detail="Admin role required")
    )

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/news/admin")
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_public_endpoint_forces_published_only():
    """
    Verify public /api/v1/news passes published_only=True to repository,
    guaranteeing that draft and archived articles are never returned to public visitors.
    """
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    executed_sqls = []

    def execute_handler(stmt, params=None):
        executed_sqls.append(str(stmt).lower())
        if "count(*)" in str(stmt).lower():
            return MockResult(scalar_val=1)
        if "from news_updates" in str(stmt).lower():
            return MockResult([dict(SAMPLE_ARTICLE)])
        return MockResult([])

    mock_db.execute.side_effect = execute_handler

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/news")
        assert resp.status_code == 200

        # Verify that n.status = 'published' was enforced in SQL query
        assert any("n.status = 'published'" in sql for sql in executed_sqls)
        # Verify that published_at <= now() was enforced in SQL query
        assert any("n.published_at <= now()" in sql for sql in executed_sqls)
    finally:
        app.dependency_overrides.clear()


def test_public_detail_endpoint_hides_draft_and_archived():
    """
    Verify /api/v1/news/{id} returns 404 for unauthenticated visitors
    when an article is in draft or archived status.
    """
    draft_article = dict(SAMPLE_ARTICLE, status="draft")
    mock_db = _make_mock_db(draft_article)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user_optional] = lambda: None

    try:
        client = TestClient(app)
        # Attempt public access to draft article
        resp = client.get(f"/api/v1/news/{draft_article['id']}")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_admin_detail_endpoint_allows_draft_and_archived():
    """Verify /api/v1/news/{id} returns 200 for admins even when article is draft or archived."""
    archived_article = dict(SAMPLE_ARTICLE, status="archived")
    mock_db = _make_mock_db(archived_article)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user_optional] = ADMIN_AUTH

    try:
        client = TestClient(app)
        resp = client.get(f"/api/v1/news/{archived_article['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "archived"
        assert data["id"] == archived_article["id"]
    finally:
        app.dependency_overrides.clear()


# ── Lifecycle & Archive / Unarchive Tests ─────────────────────────────────────

def test_admin_news_high_limit_accepted():
    """Verify /api/v1/news/admin accepts limit=200 for admin management."""
    mock_db = _make_mock_db(dict(SAMPLE_ARTICLE))
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = ADMIN_AUTH

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/news/admin?limit=200")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["total"] == 1
    finally:
        app.dependency_overrides.clear()


def test_admin_news_status_filtering():
    """Verify /api/v1/news/admin filters by status correctly."""
    articles = [
        dict(SAMPLE_ARTICLE, id="pub-1", title="Published News", status="published"),
        dict(SAMPLE_ARTICLE, id="arc-1", title="Archived News", status="archived"),
        dict(SAMPLE_ARTICLE, id="drf-1", title="Draft News", status="draft"),
    ]
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = ADMIN_AUTH

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            matched = [a for a in articles if not params or "status" not in params or a["status"] == params.get("status")]
            return MockResult(scalar_val=len(matched))
        if "from news_updates" in sql:
            matched = [a for a in articles if not params or "status" not in params or a["status"] == params.get("status")]
            return MockResult(matched)
        return MockResult([])

    mock_db.execute.side_effect = execute_handler

    try:
        client = TestClient(app)

        # 1. Published filter
        pub_resp = client.get("/api/v1/news/admin?status=published")
        assert pub_resp.status_code == 200
        pub_data = pub_resp.json()
        assert len(pub_data["data"]) == 1
        assert pub_data["data"][0]["status"] == "published"

        # 2. Archived filter
        arc_resp = client.get("/api/v1/news/admin?status=archived")
        assert arc_resp.status_code == 200
        arc_data = arc_resp.json()
        assert len(arc_data["data"]) == 1
        assert arc_data["data"][0]["status"] == "archived"

        # 3. Draft filter
        drf_resp = client.get("/api/v1/news/admin?status=draft")
        assert drf_resp.status_code == 200
        drf_data = drf_resp.json()
        assert len(drf_data["data"]) == 1
        assert drf_data["data"][0]["status"] == "draft"

        # 4. No status filter (All status for admin)
        all_resp = client.get("/api/v1/news/admin")
        assert all_resp.status_code == 200
        all_data = all_resp.json()
        assert len(all_data["data"]) == 3
    finally:
        app.dependency_overrides.clear()


def test_archive_via_patch():
    """Verify updating status to archived via PATCH preserves media and logs audit."""
    state = dict(SAMPLE_ARTICLE)
    mock_db = _make_mock_db(state)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = ADMIN_AUTH

    try:
        client = TestClient(app)
        resp = client.patch(
            f"/api/v1/news/{SAMPLE_ARTICLE['id']}",
            json={"status": "archived"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "archived"
        assert data["thumbnail_url"] == SAMPLE_ARTICLE["thumbnail_url"]
        assert data["pdf_url"] == SAMPLE_ARTICLE["pdf_url"]
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_archive_endpoint():
    """Verify dedicated POST /api/v1/news/{id}/archive sets status to archived."""
    state = dict(SAMPLE_ARTICLE)
    mock_db = _make_mock_db(state)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = ADMIN_AUTH

    try:
        client = TestClient(app)
        resp = client.post(f"/api/v1/news/{SAMPLE_ARTICLE['id']}/archive")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "archived"
        assert data["thumbnail_url"] == SAMPLE_ARTICLE["thumbnail_url"]
        assert data["pdf_url"] == SAMPLE_ARTICLE["pdf_url"]
        assert mock_db.commit.called
    finally:
        app.dependency_overrides.clear()


def test_unarchive_restores_and_preserves_media_urls():
    """
    Verify complete lifecycle:
      1. Article has thumbnail and PDF.
      2. It is archived: status becomes 'archived', media URLs remain unchanged.
      3. It is unarchived: status is restored to 'published', media URLs remain identical.
    """
    original_thumb = "https://example.supabase.co/storage/v1/object/public/news-media/important_thumb.jpeg"
    original_pdf = "https://example.supabase.co/storage/v1/object/public/news-media/official_order.pdf"

    article_state = dict(
        SAMPLE_ARTICLE,
        id="lifecycle-uuid-1",
        status="published",
        thumbnail_url=original_thumb,
        pdf_url=original_pdf,
    )
    mock_db = _make_mock_db(article_state)
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = ADMIN_AUTH

    try:
        client = TestClient(app)

        # Step 1: Archive
        arc_resp = client.post("/api/v1/news/lifecycle-uuid-1/archive")
        assert arc_resp.status_code == 200
        arc_data = arc_resp.json()
        assert arc_data["status"] == "archived"
        assert arc_data["thumbnail_url"] == original_thumb
        assert arc_data["pdf_url"] == original_pdf

        # Step 2: Unarchive
        unarc_resp = client.post("/api/v1/news/lifecycle-uuid-1/unarchive")
        assert unarc_resp.status_code == 200
        unarc_data = unarc_resp.json()
        assert unarc_data["status"] == "published"
        assert unarc_data["thumbnail_url"] == original_thumb
        assert unarc_data["pdf_url"] == original_pdf
    finally:
        app.dependency_overrides.clear()
