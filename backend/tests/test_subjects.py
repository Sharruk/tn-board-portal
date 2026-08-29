"""
Tests for GET /api/v1/subjects and GET /api/v1/subjects/{id}

These tests use FastAPI's TestClient and mock the database session dependency.
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.main import app

MOCK_SUBJECTS_CLASS_10 = [
    {
        "id": 6, "class_id": 10, "name": "Tamil", "slug": "tamil",
        "is_practical": False, "display_order": 1,
        "class_name": "Class 10", "class_slug": "10",
        "paper_count": 8,
    },
    {
        "id": 7, "class_id": 10, "name": "English", "slug": "english",
        "is_practical": False, "display_order": 2,
        "class_name": "Class 10", "class_slug": "10",
        "paper_count": 6,
    },
    {
        "id": 8, "class_id": 10, "name": "Mathematics", "slug": "maths",
        "is_practical": False, "display_order": 3,
        "class_name": "Class 10", "class_slug": "10",
        "paper_count": 12,
    },
]

MOCK_SINGLE_SUBJECT = [
    {
        "id": 8, "class_id": 10, "name": "Mathematics", "slug": "maths",
        "is_practical": False, "display_order": 3,
        "class_name": "Class 10", "class_slug": "10",
        "paper_count": 12,
    }
]


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


def _make_mock_db(list_data: list, single_data: list | None = None) -> MagicMock:
    mock_db = MagicMock()

    def _execute(stmt, params=None):
        params = params or {}
        if "subject_id" in params:
            sid = params["subject_id"]
            if single_data is not None:
                matches = [r for r in single_data if r["id"] == sid]
                return MockResult(matches)
            matches = [r for r in list_data if r["id"] == sid]
            return MockResult(matches)
        if "class_id" in params:
            cid = params["class_id"]
            matches = [r for r in list_data if r["class_id"] == cid]
            return MockResult(matches)
        return MockResult(list_data)

    mock_db.execute.side_effect = _execute
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
