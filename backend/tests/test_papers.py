"""
Tests for papers endpoints.

Tests:
  GET  /api/v1/papers                      — list (recent/popular)
  GET  /api/v1/papers/search               — search
  GET  /api/v1/papers/by-subject/{id}      — by subject
  GET  /api/v1/papers/{id}                 — single paper detail
  POST /api/v1/papers/{id}/download        — increment download count
"""

import copy
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.main import app

# ── Shared fixtures ───────────────────────────────────────────────────────────

_NOW = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat()

MOCK_PAPER_LIST_ROW = {
    "id": 42,
    "subject_id": 8,
    "exam_type": "Annual Exam",
    "year": 2024,
    "month": None,
    "district": None,
    "title": "Class 10 Maths Annual Exam 2024",
    "paper_type": "question",
    "public_url": "https://example.supabase.co/papers/uuid.pdf",
    "youtube_url": None,
    "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
    "is_visible": True,
    "status": "published",
    "download_count": 1234,
    "created_at": _NOW,
}

MOCK_PAPER_DETAIL_ROW = {
    **MOCK_PAPER_LIST_ROW,
    "subject_name": "Mathematics",
    "subject_slug": "maths",
    "is_practical": False,
    "class_id": 10,
    "class_name": "Class 10",
    "class_slug": "10",
}

MOCK_SEARCH_RAW_ROW = {
    **MOCK_PAPER_LIST_ROW,
    "subject_name": "Mathematics",
    "class_id": 10,
    "class_name": "Class 10",
}

MOCK_SEARCH_ROW = MOCK_SEARCH_RAW_ROW


class MockRow:
    def __init__(self, data: dict):
        self._mapping = data
        self._data = list(data.values())

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self._data[idx]
        return self._mapping[idx]


class MockResult:
    def __init__(self, rows: list[dict] | None = None, scalar_val=None):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


# ── Mock DB factories ─────────────────────────────────────────────────────────

def _make_list_db(data: list) -> MagicMock:
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult(data)
    return mock_db


def _make_detail_db(data: list) -> MagicMock:
    mock_db = MagicMock()
    mock_db.execute.side_effect = lambda stmt, params=None: MockResult(copy.deepcopy(data))
    return mock_db


def _make_search_db(paper_data: list, subject_data: list | None = None) -> MagicMock:
    mock_db = MagicMock()
    mock_db.execute.side_effect = lambda stmt, params=None: MockResult(copy.deepcopy(paper_data))
    return mock_db


def _make_download_db(paper_id: int, exists: bool, download_count: int = 0) -> MagicMock:
    mock_db = MagicMock()

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "update papers" in sql:
            if exists:
                return MockResult([{"id": paper_id, "download_count": download_count + 1}])
            return MockResult([])
        return MockResult([])

    mock_db.execute.side_effect = _execute
    return mock_db


# ── GET /api/v1/papers ────────────────────────────────────────────────────────

def test_list_papers_status_200():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_list_papers_response_structure():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers").json()
        assert "data" in data
        assert "count" in data
        assert "limit" in data
        assert data["count"] == 1
        assert data["limit"] == 10
    finally:
        app.dependency_overrides.clear()


def test_list_papers_item_fields():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        item = client.get("/api/v1/papers").json()["data"][0]
        assert item["id"] == 42
        assert item["exam_type"] == "Annual Exam"
        assert item["status"] == "published"
        assert item["original_filename"] == "Class10_Maths_Annual_2024_QP.pdf"
    finally:
        app.dependency_overrides.clear()


def test_list_papers_popular_sort():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers?sort=popular&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
    finally:
        app.dependency_overrides.clear()


def test_list_papers_empty():
    mock_db = _make_list_db([])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers").json()
        assert data["count"] == 0
        assert data["data"] == []
    finally:
        app.dependency_overrides.clear()


# ── GET /api/v1/papers/search ─────────────────────────────────────────────────

def test_search_papers_status_200():
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/search?q=mathematics")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_search_papers_response_structure():
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers/search?q=mathematics").json()
        assert "query" in data
        assert "total" in data
        assert "results" in data
        assert data["query"] == "mathematics"
        assert data["total"] == 1
    finally:
        app.dependency_overrides.clear()


def test_search_papers_empty_query_returns_zero_results():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers/search?q=").json()
        assert data["total"] == 0
        assert data["results"] == []
    finally:
        app.dependency_overrides.clear()


def test_search_papers_with_class_id_filter():
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/search?q=maths&class_id=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
    finally:
        app.dependency_overrides.clear()


def test_search_papers_with_all_filters():
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get(
            "/api/v1/papers/search?q=maths&class_id=10&exam_type=Annual+Exam"
            "&paper_type=question&month=March&district=Chennai"
        )
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_search_papers_deduplicates_across_terms():
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers/search?q=maths").json()
        ids = [p["id"] for p in data["results"]]
        assert len(ids) == len(set(ids)), "Search results contain duplicate paper ids"
    finally:
        app.dependency_overrides.clear()


# ── GET /api/v1/papers/by-subject/{id} ────────────────────────────────────────

def test_list_by_subject_status_200():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/by-subject/8")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_list_by_subject_empty():
    mock_db = _make_list_db([])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers/by-subject/999").json()
        assert data["count"] == 0
        assert data["data"] == []
    finally:
        app.dependency_overrides.clear()


def test_list_by_subject_with_exam_type_filter():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/by-subject/8?exam_type=Annual+Exam")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_list_by_subject_with_paper_type_filter():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/by-subject/8?paper_type=question")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


# ── GET /api/v1/papers/{id} ───────────────────────────────────────────────────

def test_get_paper_status_200():
    mock_db = _make_detail_db([MOCK_PAPER_DETAIL_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/42")
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_get_paper_not_found_returns_404():
    mock_db = _make_detail_db([])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/9999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_paper_response_fields():
    mock_db = _make_detail_db([MOCK_PAPER_DETAIL_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        body = client.get("/api/v1/papers/42").json()
        expected = (
            "id", "subject_id", "exam_type", "year", "month", "district",
            "title", "paper_type", "public_url", "youtube_url",
            "original_filename", "is_visible", "status", "download_count",
            "created_at", "subject_name", "subject_slug", "is_practical",
            "class_id", "class_name", "class_slug",
        )
        for field in expected:
            assert field in body, f"Missing field: {field}"
    finally:
        app.dependency_overrides.clear()


# ── POST /api/v1/papers/{id}/download ─────────────────────────────────────────

def test_record_download_status_204():
    mock_db = _make_download_db(paper_id=42, exists=True, download_count=5)
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.dependencies.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "test@example.com", "firebase_uid": "testuid"}
    try:
        client = TestClient(app)
        resp = client.post("/api/v1/papers/42/download")
        assert resp.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_record_download_not_found_returns_404():
    mock_db = _make_download_db(paper_id=9999, exists=False)
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.dependencies.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "test@example.com", "firebase_uid": "testuid"}
    try:
        client = TestClient(app)
        resp = client.post("/api/v1/papers/9999/download")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ── Term expansion unit tests ─────────────────────────────────────────────────

def test_term_expansion_maths():
    from app.services.papers_service import _expand_terms
    terms = _expand_terms("maths")
    assert "maths" in terms
    assert "mathematics" in terms


def test_term_expansion_no_expansion_for_full_word():
    from app.services.papers_service import _expand_terms
    terms = _expand_terms("mathematics")
    assert "mathematics" in terms


def test_term_expansion_preserves_original():
    from app.services.papers_service import _expand_terms
    terms = _expand_terms("annual exam")
    assert "annual exam" in terms


def test_term_expansion_empty_string():
    from app.services.papers_service import _expand_terms
    terms = _expand_terms("")
    assert "" in terms


# ── Download file GET endpoint tests & Privacy checks ───────────────────────────

def test_get_download_paper_file_success(monkeypatch):
    import httpx
    from app.dependencies.supabase import get_db

    mock_db = _make_detail_db([MOCK_PAPER_DETAIL_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db

    # Mock httpx.AsyncClient.get
    async def mock_get(self, url, **kwargs):
        class MockResp:
            status_code = 200
            content = b"%PDF-1.4 sample paper binary content"
        return MockResp()

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/42/download")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert 'attachment; filename="Class10_Maths_Annual_2024_QP.pdf"' in resp.headers["content-disposition"]
        assert resp.content == b"%PDF-1.4 sample paper binary content"
    finally:
        app.dependency_overrides.clear()


def test_get_download_paper_file_not_found():
    from app.dependencies.supabase import get_db

    mock_db = _make_detail_db([])
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/999/download")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_paper_response_includes_description_and_preserves_privacy():
    from app.dependencies.supabase import get_db

    paper_with_contributor = {
        **MOCK_PAPER_DETAIL_ROW,
        "description": "Comprehensive question paper with complete syllabus coverage.",
        "contributor_name": "Sharruk S",
        "submission_id": "f5321f3f-dd55-457d-ad62-75f05482a77b",
    }
    mock_db = _make_detail_db([paper_with_contributor])
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/42")
        assert resp.status_code == 200
        data = resp.json()
        assert data["description"] == "Comprehensive question paper with complete syllabus coverage."
        assert data["contributor_name"] == "Sharruk S"
        assert data["submission_id"] == "f5321f3f-dd55-457d-ad62-75f05482a77b"
        # Strict privacy check: email must NEVER be present in public paper response
        assert "email" not in data
        assert "contributor_email" not in data
        assert "submitter_email" not in data
    finally:
        app.dependency_overrides.clear()


# ── Delete Paper Tests ────────────────────────────────────────────────────────

def test_delete_paper_as_admin_success():
    from app.dependencies.auth import require_admin
    from app.dependencies.supabase import get_db

    mock_db = _make_detail_db([
        {
            **MOCK_PAPER_DETAIL_ROW,
            "file_path": "uuid-1234.pdf",
            "submission_id": "sub-1234",
            "contributor_name": "Sharruk",
        }
    ])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "firebase_uid": "admin-uid-123",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.delete("/api/v1/papers/42")
        assert resp.status_code == 200
        data = resp.json()
        assert data["paper_id"] == 42
        assert data["deleted"] is True
        assert "deleted successfully" in data["message"]
    finally:
        app.dependency_overrides.clear()


def test_delete_paper_missing_storage_resilience():
    from app.dependencies.auth import require_admin
    from app.dependencies.supabase import get_db

    mock_db = _make_detail_db([
        {
            **MOCK_PAPER_DETAIL_ROW,
            "file_path": "missing-file.pdf",
        }
    ])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "firebase_uid": "admin-uid-123",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.delete("/api/v1/papers/42")
        assert resp.status_code == 200
        data = resp.json()
        assert data["paper_id"] == 42
        assert data["deleted"] is True
    finally:
        app.dependency_overrides.clear()


def test_delete_paper_not_found():
    from app.dependencies.auth import require_admin
    from app.dependencies.supabase import get_db

    mock_db = _make_detail_db([])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "firebase_uid": "admin-uid-123",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.delete("/api/v1/papers/99999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_delete_paper_unauthenticated():
    from app.dependencies.supabase import get_db

    mock_db = _make_detail_db([MOCK_PAPER_DETAIL_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        # Calling without auth token
        resp = client.delete("/api/v1/papers/42")
        assert resp.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


# ── Regression tests for missing column resilience (UndefinedColumn) ─────────

def test_get_paper_fallback_when_description_column_undefined():
    """
    Regression test for:
    psycopg2.errors.UndefinedColumn: column p.description does not exist
    Verifies that if PostgreSQL lacks the `description` column, get_paper()
    gracefully falls back and returns 200 with description=None.
    """
    from app.dependencies.supabase import get_db

    mock_db = MagicMock()
    call_count = {"count": 0}

    def _execute(stmt, params=None):
        call_count["count"] += 1
        sql = str(stmt).lower()
        if "p.description" in sql:
            # Simulate psycopg2 UndefinedColumn error
            raise Exception("psycopg2.errors.UndefinedColumn: column p.description does not exist")
        # Fallback query succeeds
        row_without_desc = {
            k: v for k, v in MOCK_PAPER_DETAIL_ROW.items() if k != "description"
        }
        return MockResult([row_without_desc])

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/42")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 42
        assert data["title"] == "Class 10 Maths Annual Exam 2024"
        assert data["description"] is None
        assert data["status"] == "published"
        assert call_count["count"] == 2  # Primary failed, fallback succeeded
    finally:
        app.dependency_overrides.clear()


def test_get_paper_fallback_when_all_optional_columns_undefined():
    """
    Regression test verifying fallback 2 succeeds even if description,
    submission_id, and contributor_name columns are all absent in legacy schema.
    """
    from app.dependencies.supabase import get_db

    mock_db = MagicMock()
    call_count = {"count": 0}

    def _execute(stmt, params=None):
        call_count["count"] += 1
        sql = str(stmt).lower()
        if "p.description" in sql:
            raise Exception("psycopg2.errors.UndefinedColumn: column p.description does not exist")
        if "p.submission_id" in sql or "p.contributor_name" in sql:
            raise Exception("psycopg2.errors.UndefinedColumn: column p.submission_id does not exist")
        # Fallback 2 (core legacy columns) succeeds
        core_row = {
            "id": 25,
            "subject_id": 8,
            "exam_type": "First Mid Term Test",
            "year": 2026,
            "month": "July",
            "district": "Chennai",
            "title": "Class 10 Science First Mid Term Test July 2026",
            "paper_type": "question",
            "file_path": "uuid-25.pdf",
            "public_url": "https://example.supabase.co/storage/v1/object/public/papers/uuid-25.pdf",
            "youtube_url": None,
            "original_filename": "Class10_Science_QP.pdf",
            "is_visible": True,
            "download_count": 50,
            "created_at": _NOW,
            "subject_name": "Science",
            "subject_slug": "science",
            "is_practical": True,
            "class_id": 10,
            "class_name": "Class 10",
            "class_slug": "10",
        }
        return MockResult([core_row])

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/papers/25")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 25
        assert data["title"] == "Class 10 Science First Mid Term Test July 2026"
        assert data["description"] is None
        assert data["contributor_name"] is None
        assert data["submission_id"] is None
        assert data["status"] == "published"
        assert call_count["count"] == 3  # Primary -> Fallback 1 -> Fallback 2
    finally:
        app.dependency_overrides.clear()


def test_list_recent_and_popular_fallback_when_contributor_columns_undefined():
    """
    Regression test verifying that list_recent and list_popular gracefully fall back
    when contributor_name/submission_id columns are missing in legacy DB schema.
    """
    from app.dependencies.supabase import get_db

    mock_db = MagicMock()
    call_count = {"count": 0}

    core_row = {
        "id": 101,
        "subject_id": 8,
        "exam_type": "Annual Exam",
        "year": 2026,
        "month": "March",
        "district": "Chennai",
        "title": "Class 10 Maths Annual 2026",
        "paper_type": "question",
        "public_url": "https://example.com/p101.pdf",
        "youtube_url": None,
        "original_filename": "Maths_Annual.pdf",
        "is_visible": True,
        "download_count": 120,
        "created_at": _NOW,
    }

    def _execute(stmt, params=None):
        call_count["count"] += 1
        sql = str(stmt).lower()
        if "contributor_name" in sql or "submission_id" in sql:
            raise Exception("psycopg2.errors.UndefinedColumn: column contributor_name does not exist")
        return MockResult([core_row])

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)
        # Test recent
        resp = client.get("/api/v1/papers?sort=recent&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == 101
        assert data["data"][0]["contributor_name"] is None

        # Test popular
        resp_pop = client.get("/api/v1/papers?sort=popular&limit=10")
        assert resp_pop.status_code == 200
        data_pop = resp_pop.json()
        assert len(data_pop["data"]) == 1
        assert data_pop["data"][0]["id"] == 101
    finally:
        app.dependency_overrides.clear()


def test_critical_regression_paper_catalog_and_contributor_isolation():
    """
    CRITICAL REGRESSION TEST:
    Scenario with:
      A. Existing normal published paper (contributor_name=None, submission_id=None)
      B. Existing contributor-submitted published paper (contributor_name='Alice', submission_id='...')
      C. Contributor with zero published contributions ('Bob', 0 approved)

    Expected:
      - A appears on paper list (GET /api/v1/papers).
      - B appears on paper list (GET /api/v1/papers) with contributor attribution.
      - C does not appear in top contributors (GET /api/v1/leaderboard with approved_count > 0 filter).
      - Contributor filtering logic has NO effect on the paper catalog.
    """
    from app.dependencies.supabase import get_db

    mock_db = MagicMock()

    # Paper A: Normal published paper
    paper_a = {
        "id": 1,
        "subject_id": 8,
        "exam_type": "Annual Exam",
        "year": 2026,
        "month": "March",
        "district": "Chennai",
        "title": "Standard Admin Uploaded Paper A",
        "paper_type": "question",
        "public_url": "https://example.com/p1.pdf",
        "youtube_url": None,
        "original_filename": "Paper_A.pdf",
        "is_visible": True,
        "download_count": 10,
        "contributor_name": None,
        "submission_id": None,
        "created_at": _NOW,
    }

    # Paper B: Contributor-submitted published paper
    paper_b = {
        "id": 2,
        "subject_id": 8,
        "exam_type": "Annual Exam",
        "year": 2026,
        "month": "March",
        "district": "Madurai",
        "title": "Community Contributed Paper B",
        "paper_type": "question",
        "public_url": "https://example.com/p2.pdf",
        "youtube_url": None,
        "original_filename": "Paper_B.pdf",
        "is_visible": True,
        "download_count": 20,
        "contributor_name": "Alice Star",
        "submission_id": "00000000-0000-0000-0000-000000000001",
        "created_at": _NOW,
    }

    # Raw submissions for leaderboard
    # Alice has 1 approved submission.
    # Bob has 1 pending / 0 approved submissions.
    leaderboard_raw_subs = [
        {
            "publisher_name": "Alice Star",
            "firebase_uid": "uid_alice",
            "status": "approved",
            "file_count": 1,
        },
        {
            "publisher_name": "Bob Zero",
            "firebase_uid": "uid_bob",
            "status": "pending",
            "file_count": 1,
        },
    ]

    def _execute(stmt, params=None):
        sql = str(stmt).lower()
        if "from papers" in sql:
            return MockResult([paper_a, paper_b])
        if "from submissions" in sql:
            return MockResult(leaderboard_raw_subs)
        return MockResult([])

    mock_db.execute.side_effect = _execute
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        client = TestClient(app)

        # 1. Verify paper catalog returns BOTH Paper A and Paper B
        papers_resp = client.get("/api/v1/papers?sort=recent&limit=10")
        assert papers_resp.status_code == 200
        paper_items = papers_resp.json()["data"]
        paper_ids = [p["id"] for p in paper_items]
        assert 1 in paper_ids, "Paper A (normal published paper) must appear in catalog"
        assert 2 in paper_ids, "Paper B (contributor-submitted paper) must appear in catalog"

        paper_a_item = next(p for p in paper_items if p["id"] == 1)
        paper_b_item = next(p for p in paper_items if p["id"] == 2)
        assert paper_a_item["contributor_name"] is None
        assert paper_b_item["contributor_name"] == "Alice Star"

        # 2. Verify leaderboard / Top Contributors
        lb_resp = client.get("/api/v1/leaderboard?limit=5")
        assert lb_resp.status_code == 200
        contributors = lb_resp.json()["data"]

        # Filter active top contributors as frontend HomePage does: (c.approved_count > 0)
        active_top_contributors = [
            c for c in contributors if c.get("approved_count", 0) > 0
        ]
        top_names = [c["contributor_name"] for c in active_top_contributors]
        assert "Alice Star" in top_names, "Alice (with approved paper) must be present in Top Contributors"
        assert "Bob Zero" not in top_names, "Bob (with 0 approved contributions) must NOT appear in Top Contributors"

        # 3. Prove that paper catalog count is totally unaffected by contributor count
        assert len(paper_items) == 2
    finally:
        app.dependency_overrides.clear()




