"""
Tests for papers endpoints.

Tests:
  GET  /api/v1/papers                      — list (recent/popular)
  GET  /api/v1/papers/search               — search via RPC
  GET  /api/v1/papers/by-subject/{id}      — by subject
  GET  /api/v1/papers/{id}                 — single paper detail
  POST /api/v1/papers/{id}/download        — increment download count

All Supabase calls are mocked via dependency_overrides[get_db].
No real database connection is required.

Mock data mirrors the exact shape Supabase returns:
  - Direct table queries return flat dicts (matching _LIST_SELECT columns)
  - Detail queries return nested dicts with "subjects" → "classes" structure
  - RPC calls return flat dicts (matching search_papers() RETURNS TABLE)
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.main import app

# ── Shared fixtures ───────────────────────────────────────────────────────────

_NOW = datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat()

# Shape that list_recent / list_popular / list_by_subject return.
# NOTE: No 'status' column — the repository synthesises it from is_visible.
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

# Shape that get_by_id returns (with nested subjects → classes).
# NOTE: No 'status' column in the DB row; the repository synthesises it.
MOCK_PAPER_DETAIL_ROW = {
    **MOCK_PAPER_LIST_ROW,
    "file_path": "uuid.pdf",
    "subjects": {
        "id": 8,
        "name": "Mathematics",
        "slug": "maths",
        "is_practical": False,
        "classes": {"id": 10, "name": "Class 10", "slug": "10"},
    },
}

# Shape that the new PostgREST-based search returns (replaces RPC).
# The repository normalises the nested subjects/classes join before returning.
MOCK_SEARCH_RAW_ROW = {
    "id": 42,
    "subject_id": 8,
    "exam_type": "Annual Exam",
    "year": 2024,
    "month": None,
    "district": None,
    "title": "Class 10 Maths Annual Exam 2024",
    "paper_type": "question",
    "public_url": "https://example.supabase.co/papers/uuid.pdf",
    "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
    "is_visible": True,
    "download_count": 1234,
    "created_at": _NOW,
    # Nested join shape as PostgREST returns it (before normalisation)
    "subjects": {
        "id": 8,
        "name": "Mathematics",
        "slug": "maths",
        "classes": {"id": 10, "name": "Class 10"},
    },
}

# Legacy alias kept so any remaining tests that reference MOCK_SEARCH_ROW still compile.
MOCK_SEARCH_ROW = {
    "id": 42,
    "subject_id": 8,
    "exam_type": "Annual Exam",
    "year": 2024,
    "month": None,
    "district": None,
    "title": "Class 10 Maths Annual Exam 2024",
    "paper_type": "question",
    "file_path": "uuid.pdf",
    "public_url": "https://example.supabase.co/papers/uuid.pdf",
    "youtube_url": None,
    "original_filename": "Class10_Maths_Annual_2024_QP.pdf",
    "is_visible": True,
    "status": "published",
    "download_count": 1234,
    "created_at": _NOW,
    "subject_name": "Mathematics",
    "class_id": 10,
    "class_name": "Class 10",
}


# ── Mock DB factory ───────────────────────────────────────────────────────────

def _make_list_db(data: list) -> MagicMock:
    """
    Mock for list endpoints: table().select().eq().order().limit().execute()
    All chaining returns self so any order of calls works.
    """
    mock_db = MagicMock()
    response = MagicMock()
    response.data = data

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = response

    mock_db.table.return_value = query
    return mock_db


def _make_detail_db(data: list) -> MagicMock:
    """
    Mock for get_by_id: table().select().eq().eq().execute()
    Returns a deep copy of data each time execute() is called so that
    _normalise_detail's dict.pop() calls don't mutate the shared fixture.
    """
    import copy

    mock_db = MagicMock()

    def _fresh_response():
        response = MagicMock()
        response.data = copy.deepcopy(data)
        return response

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.side_effect = _fresh_response

    mock_db.table.return_value = query
    return mock_db


def _make_rpc_db(data: list) -> MagicMock:
    """
    Mock for RPC calls: db.rpc(name, params).execute()
    Kept for backward compatibility with any legacy test helpers.
    """
    mock_db = MagicMock()
    rpc_response = MagicMock()
    rpc_response.data = data

    rpc_chain = MagicMock()
    rpc_chain.execute.return_value = rpc_response

    mock_db.rpc.return_value = rpc_chain
    return mock_db


def _make_search_db(paper_data: list, subject_data: list | None = None) -> MagicMock:
    """
    Mock for the new PostgREST-based search.

    The new search() method does:
      1. db.table("papers").select(...).eq(...).or_(...).order(...).limit(...).execute()
      2. db.table("subjects").select(...).or_(...).execute()  ← subject-name fallback
      3. db.table("papers").select(...).eq(...).in_(...).order(...).limit(...).execute()

    We return paper_data for ALL paper table calls and empty list for subjects.
    This ensures the primary OR query returns results and the secondary subject
    fallback returns nothing (avoiding duplicate ids in de-duplication).
    """
    import copy

    mock_db = MagicMock()

    paper_response = MagicMock()
    paper_response.data = copy.deepcopy(paper_data)

    subj_response = MagicMock()
    subj_response.data = subject_data if subject_data is not None else []

    call_count = [0]

    def table_side_effect(table_name: str):
        query = MagicMock()
        if table_name == "papers":
            query.select.return_value = query
            query.eq.return_value = query
            query.or_.return_value = query
            query.order.return_value = query
            query.limit.return_value = query
            query.ilike.return_value = query
            query.in_.return_value = query
            query.execute.return_value = copy.deepcopy(paper_response)
        else:  # subjects
            query.select.return_value = query
            query.or_.return_value = query
            query.execute.return_value = subj_response
        return query

    mock_db.table.side_effect = table_side_effect
    return mock_db


def _make_download_db(paper_id: int, exists: bool, download_count: int = 0) -> MagicMock:
    """
    Mock for record_download.

    The new implementation does:
      1. db.table("papers").select("id, download_count").eq("id", ...).eq("is_visible", True).execute()
         → returns [paper row] if exists else []
      2. db.table("papers").update({"download_count": N+1}).eq("id", ...).execute()
    """
    mock_db = MagicMock()

    check_response = MagicMock()
    check_response.data = [{"id": paper_id, "download_count": download_count}] if exists else []

    update_response = MagicMock()
    update_response.data = [{"id": paper_id, "download_count": download_count + 1}] if exists else []

    call_count = [0]

    def table_side_effect(table_name: str):
        nonlocal call_count
        query = MagicMock()
        call_count[0] += 1
        if call_count[0] == 1:
            # First call: SELECT (check existence)
            query.select.return_value = query
            query.eq.return_value = query
            query.execute.return_value = check_response
        else:
            # Second call: UPDATE
            query.update.return_value = query
            query.eq.return_value = query
            query.execute.return_value = update_response
        return query

    mock_db.table.side_effect = table_side_effect
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
# The repository now uses a direct PostgREST query instead of the search_papers()
# RPC (which references the missing 'status' column).
# Mocks use _make_search_db() which handles the two-table query pattern.

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
        assert data["query"] == "mathematics"
        assert data["total"] == 1
        assert len(data["results"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_search_papers_result_fields():
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        result = client.get("/api/v1/papers/search?q=maths").json()["results"][0]
        # All PaperSearchResult fields must be present
        for field in ("id", "title", "exam_type", "year", "paper_type",
                      "subject_name", "class_name", "class_id", "status"):
            assert field in result, f"Missing field: {field}"
    finally:
        app.dependency_overrides.clear()


def test_search_papers_empty_query_returns_zero():
    mock_db = _make_search_db([])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers/search?q=").json()
        assert data["total"] == 0
        assert data["results"] == []
    finally:
        app.dependency_overrides.clear()


def test_search_papers_with_all_filters():
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get(
            "/api/v1/papers/search"
            "?q=maths&class_id=10&exam_type=Annual+Exam"
            "&paper_type=question&month=July&district=Chennai"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "maths"
    finally:
        app.dependency_overrides.clear()


def test_search_deduplicates_by_id():
    """Two queries that match the same paper id should return it once."""
    import copy
    mock_db = _make_search_db([MOCK_SEARCH_RAW_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        # 'maths' may expand to multiple terms but de-duplication ensures 1 result
        data = client.get("/api/v1/papers/search?q=maths").json()
        assert data["total"] == 1  # deduplicated
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


def test_list_by_subject_returns_list():
    mock_db = _make_list_db([MOCK_PAPER_LIST_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers/by-subject/8").json()
        assert data["count"] == 1
        assert data["data"][0]["id"] == 42
    finally:
        app.dependency_overrides.clear()


def test_list_by_subject_empty():
    mock_db = _make_list_db([])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/papers/by-subject/999").json()
        assert data["count"] == 0
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


def test_get_paper_response_fields():
    mock_db = _make_detail_db([MOCK_PAPER_DETAIL_ROW])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        body = client.get("/api/v1/papers/42").json()
        assert body["id"] == 42
        assert body["subject_name"] == "Mathematics"
        assert body["subject_slug"] == "maths"
        assert body["class_id"] == 10
        assert body["class_name"] == "Class 10"
        assert body["class_slug"] == "10"
        assert body["is_practical"] is False
        assert body["status"] == "published"
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


def test_get_paper_all_fields_present():
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
# The repository now uses a direct PostgREST read-modify-write instead of the
# increment_download_count() RPC (which references the missing 'status' column).

def test_record_download_status_204():
    mock_db = _make_download_db(paper_id=42, exists=True, download_count=5)
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.dependencies.auth import get_current_user
    from app.db.supabase_client import get_supabase_admin_client
    app.dependency_overrides[get_supabase_admin_client] = lambda: MagicMock()
    app.dependency_overrides[get_current_user] = lambda: {"role": "USER", "email": "test@example.com", "firebase_uid": "testuid"}
    try:
        client = TestClient(app)
        resp = client.post("/api/v1/papers/42/download")
        assert resp.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_record_download_not_found_returns_404():
    # exists=False → check query returns [] → repository raises ValueError → service → 404
    mock_db = _make_download_db(paper_id=9999, exists=False)
    app.dependency_overrides[get_db] = lambda: mock_db
    from app.dependencies.auth import get_current_user
    from app.db.supabase_client import get_supabase_admin_client
    app.dependency_overrides[get_supabase_admin_client] = lambda: MagicMock()
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
