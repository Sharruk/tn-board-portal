"""
Tests for GET /api/v1/classes and GET /api/v1/classes/{id}

These tests use FastAPI's TestClient and mock the Supabase dependency
so no real database connection is needed.

Test strategy:
  - Override get_db() dependency with a mock that returns controlled data
  - Test happy paths (200 responses + correct body shape)
  - Test error paths (404 for unknown ids)
  - Test response schema validation
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.main import app
from app.dependencies.supabase import get_db

# ── Fixtures ──────────────────────────────────────────────────────────────────

# Raw rows as Supabase would return them (with nested aggregate syntax)
MOCK_CLASSES_RAW = [
    {"id": 9,  "name": "Class 9",  "slug": "9",  "subjects": [{"count": 5}]},
    {"id": 10, "name": "Class 10", "slug": "10", "subjects": [{"count": 5}]},
    {"id": 11, "name": "Class 11", "slug": "11", "subjects": [{"count": 11}]},
    {"id": 12, "name": "Class 12", "slug": "12", "subjects": [{"count": 11}]},
]


def _make_mock_db(list_data: list, single_data: list | None = None) -> MagicMock:
    """
    Build a mock Supabase client.

    The repository uses two distinct call chains:
      - list_all():   table().select().order().execute()   → list_data
      - get_by_id():  table().select().eq().execute()      → single_data

    We create separate query objects for each path so the execute()
    side_effect sequences never interfere with each other.
    """
    mock_db = MagicMock()

    list_response = MagicMock()
    list_response.data = list_data

    single_response = MagicMock()
    single_response.data = single_data if single_data is not None else list_data[:1]

    # Query object for get_by_id: .eq().execute() → single_response
    eq_query = MagicMock()
    eq_query.execute.return_value = single_response

    # Query object for list_all: .order().execute() → list_response
    # .eq() on this object returns the eq_query so get_by_id works correctly.
    list_query = MagicMock()
    list_query.order.return_value = list_query
    list_query.execute.return_value = list_response
    list_query.eq.return_value = eq_query

    mock_db.table.return_value.select.return_value = list_query
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
    single = [{"id": 10, "name": "Class 10", "slug": "10", "subjects": [{"count": 5}]}]
    mock_db = _make_mock_db(MOCK_CLASSES_RAW, single_data=single)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        # First call = list (not used here), second call = eq().execute()
        # Use a fresh client with only the single mock
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
    single = [{"id": 9, "name": "Class 9", "slug": "9", "subjects": [{"count": 5}]}]
    mock_db = _make_mock_db(MOCK_CLASSES_RAW, single_data=single)
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        client = TestClient(app)
        body = client.get("/api/v1/classes/9").json()
        for field in ("id", "name", "slug", "subject_count"):
            assert field in body, f"Missing field: {field}"
    finally:
        app.dependency_overrides.clear()
