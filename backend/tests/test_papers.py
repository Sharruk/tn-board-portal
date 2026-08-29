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
