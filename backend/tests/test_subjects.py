"""
Tests for GET /api/v1/subjects and GET /api/v1/subjects/{id}

These tests use FastAPI's TestClient and mock the Supabase dependency
so no real database connection is needed.

Test strategy:
  - Override get_db() dependency with a mock that returns controlled data
  - Test happy paths (200 responses + correct body shape)
  - Test class_id query parameter filtering
  - Test error paths (404 for unknown ids)
  - Test response schema validation
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.main import app

# ── Fixtures ──────────────────────────────────────────────────────────────────

# Raw rows as Supabase would return them (with nested join syntax)
MOCK_SUBJECTS_CLASS_10 = [
    {
        "id": 6, "class_id": 10, "name": "Tamil", "slug": "tamil",
        "is_practical": False, "display_order": 1,
        "classes": {"id": 10, "name": "Class 10", "slug": "10"},
        "papers": [{"count": 8}],
    },
    {
        "id": 7, "class_id": 10, "name": "English", "slug": "english",
        "is_practical": False, "display_order": 2,
        "classes": {"id": 10, "name": "Class 10", "slug": "10"},
        "papers": [{"count": 6}],
    },
    {
        "id": 8, "class_id": 10, "name": "Mathematics", "slug": "maths",
        "is_practical": False, "display_order": 3,
        "classes": {"id": 10, "name": "Class 10", "slug": "10"},
        "papers": [{"count": 12}],
    },
]

MOCK_SINGLE_SUBJECT = [
    {
        "id": 8, "class_id": 10, "name": "Mathematics", "slug": "maths",
        "is_practical": False, "display_order": 3,
        "classes": {"id": 10, "name": "Class 10", "slug": "10"},
        "papers": [{"count": 12}],
    }
]


def _make_mock_db(list_data: list, single_data: list | None = None) -> MagicMock:
    """
    Build a mock Supabase client.

    The repository uses two distinct call chains:
      - list_all/list_by_class:  table().select().order().order().execute()  → list_data
      - get_by_id:               table().select().eq().execute()             → single_data

    We create separate query objects for each path so execute() results
    never cross-contaminate between list and get-by-id calls.
    """
    mock_db = MagicMock()

    list_response = MagicMock()
    list_response.data = list_data

    single_response = MagicMock()
    single_response.data = single_data if single_data is not None else list_data[:1]

    # eq path → single_response
    eq_query = MagicMock()
    eq_query.execute.return_value = single_response

    # order path → list_response; .eq() on order path also returns eq_query
    list_query = MagicMock()
    list_query.order.return_value = list_query
    list_query.execute.return_value = list_response
    list_query.eq.return_value = eq_query

    mock_db.table.return_value.select.return_value = list_query
    return mock_db


# ── List subjects ─────────────────────────────────────────────────────────────

def test_list_subjects_status_200():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/subjects")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_list_subjects_count():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/subjects").json()
        assert data["count"] == 3
        assert len(data["data"]) == 3
    finally:
        app.dependency_overrides.clear()


def test_list_subjects_with_class_id_filter():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/subjects?class_id=10").json()
        assert data["class_id"] == 10
        assert all(s["class_id"] == 10 for s in data["data"])
    finally:
        app.dependency_overrides.clear()


def test_list_subjects_no_filter_returns_null_class_id():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/subjects").json()
        assert data["class_id"] is None
    finally:
        app.dependency_overrides.clear()


def test_list_subjects_structure():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/subjects").json()
        subject = data["data"][2]  # Mathematics
        assert subject["name"] == "Mathematics"
        assert subject["slug"] == "maths"
        assert subject["class_name"] == "Class 10"
        assert subject["paper_count"] == 12
    finally:
        app.dependency_overrides.clear()


# ── Get single subject ────────────────────────────────────────────────────────

def test_get_subject_status_200():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10, single_data=MOCK_SINGLE_SUBJECT)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/subjects/8")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_get_subject_response_body():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10, single_data=MOCK_SINGLE_SUBJECT)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        body = client.get("/api/v1/subjects/8").json()
        assert body["id"] == 8
        assert body["name"] == "Mathematics"
        assert body["class_name"] == "Class 10"
        assert body["class_slug"] == "10"
        assert body["paper_count"] == 12
        assert body["is_practical"] is False
    finally:
        app.dependency_overrides.clear()


def test_get_subject_not_found_returns_404():
    mock_db = _make_mock_db([], single_data=[])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/subjects/9999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_subject_response_fields_present():
    mock_db = _make_mock_db(MOCK_SUBJECTS_CLASS_10, single_data=MOCK_SINGLE_SUBJECT)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        body = client.get("/api/v1/subjects/8").json()
        expected_fields = (
            "id", "class_id", "name", "slug",
            "is_practical", "display_order",
            "class_name", "class_slug", "paper_count",
        )
        for field in expected_fields:
            assert field in body, f"Missing field: {field}"
    finally:
        app.dependency_overrides.clear()
