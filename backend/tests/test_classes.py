"""
Tests for GET /api/v1/classes and GET /api/v1/classes/{id}

These tests use FastAPI's TestClient and mock the database session dependency.
"""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.supabase import get_db

MOCK_CLASSES_RAW = [
    {"id": 9,  "name": "Class 9",  "slug": "9",  "subject_count": 5},
    {"id": 10, "name": "Class 10", "slug": "10", "subject_count": 5},
    {"id": 11, "name": "Class 11", "slug": "11", "subject_count": 11},
    {"id": 12, "name": "Class 12", "slug": "12", "subject_count": 11},
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
        if "class_id" in params:
            cid = params["class_id"]
            if single_data is not None:
                matches = [r for r in single_data if r["id"] == cid]
                return MockResult(matches)
            matches = [r for r in list_data if r["id"] == cid]
            return MockResult(matches)
        return MockResult(list_data)

    mock_db.execute.side_effect = _execute
    return mock_db


# ── List classes ──────────────────────────────────────────────────────────────

def test_list_classes_status_200():
    mock_db = _make_mock_db(MOCK_CLASSES_RAW)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/classes")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_list_classes_count():
    mock_db = _make_mock_db(MOCK_CLASSES_RAW)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/classes").json()
        assert data["count"] == 4
        assert len(data["data"]) == 4
    finally:
        app.dependency_overrides.clear()


def test_list_classes_structure():
    mock_db = _make_mock_db(MOCK_CLASSES_RAW)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/classes").json()
        first = data["data"][0]
        assert first["id"] == 9
        assert first["name"] == "Class 9"
        assert first["slug"] == "9"
        assert first["subject_count"] == 5
    finally:
        app.dependency_overrides.clear()


def test_list_classes_subject_count_correct():
    mock_db = _make_mock_db(MOCK_CLASSES_RAW)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        data = client.get("/api/v1/classes").json()
        classes_map = {c["id"]: c for c in data["data"]}
        assert classes_map[9]["subject_count"] == 5
        assert classes_map[10]["subject_count"] == 5
        assert classes_map[11]["subject_count"] == 11
        assert classes_map[12]["subject_count"] == 11
    finally:
        app.dependency_overrides.clear()


# ── Get single class ──────────────────────────────────────────────────────────

def test_get_class_10_status_200():
    single = [{"id": 10, "name": "Class 10", "slug": "10", "subject_count": 5}]
    mock_db = _make_mock_db(MOCK_CLASSES_RAW, single_data=single)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/classes/10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == 10
        assert body["subject_count"] == 5
    finally:
        app.dependency_overrides.clear()


def test_get_class_not_found_returns_404():
    mock_db = _make_mock_db([], single_data=[])
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        response = client.get("/api/v1/classes/99")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_get_class_response_fields_present():
    single = [{"id": 9, "name": "Class 9", "slug": "9", "subject_count": 5}]
    mock_db = _make_mock_db(MOCK_CLASSES_RAW, single_data=single)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        body = client.get("/api/v1/classes/9").json()
        for field in ("id", "name", "slug", "subject_count"):
            assert field in body, f"Missing field: {field}"
    finally:
        app.dependency_overrides.clear()
