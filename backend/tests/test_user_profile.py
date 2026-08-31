"""
Tests for User Profile endpoints:
  - GET /api/v1/users/me
  - PATCH /api/v1/users/me
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.dependencies.auth import get_current_user
from app.main import app


class MockRow:
    def __init__(self, data: dict | tuple):
        if isinstance(data, dict):
            self._mapping = data
            self._data = list(data.values())
        else:
            self._mapping = {f"col_{i}": v for i, v in enumerate(data)}
            self._data = list(data)

    def __getitem__(self, idx):
        if isinstance(idx, int):
            return self._data[idx]
        return self._mapping[idx]


class MockResult:
    def __init__(self, rows: list[dict | tuple] | None = None, scalar_val=None):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


_USER = {
    "id": "11111111-1111-1111-1111-111111111111",
    "firebase_uid": "user-uid-123",
    "email": "sharruk@example.com",
    "display_name": "Sharruk",
    "role": "USER",
    "is_active": True,
    "photo_url": "https://example.com/photo.jpg",
}


@pytest.fixture
def client():
    return TestClient(app)


def test_get_my_profile_unauthenticated(client):
    """Unauthenticated call returns 401."""
    res = client.get("/api/v1/users/me")
    assert res.status_code == 401


def test_get_my_profile_success(client):
    """Authenticated user can fetch their own profile."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "from users" in sql:
            return MockResult([_USER])
        if "count(*)" in sql and "from submissions" in sql:
            # Return stats
            return MockResult([("approved", 6), ("pending", 1), ("rejected", 1)])
        return MockResult([])

    mock_db.execute.side_effect = _exec

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _USER

    try:
        res = client.get("/api/v1/users/me", headers={"Authorization": "Bearer token"})
        assert res.status_code == 200
        data = res.json()
        assert data["display_name"] == "Sharruk"
        assert data["email"] == "sharruk@example.com"
        assert data["badge"] == "⭐ Active Contributor"
        assert data["stats"]["published_count"] == 6
        assert data["stats"]["pending_count"] == 1
        assert data["stats"]["rejected_count"] == 1
        assert data["stats"]["total_submissions"] == 8
    finally:
        app.dependency_overrides.clear()


def test_update_display_name_success(client):
    """Authenticated user can update their display contribution name."""
    mock_db = MagicMock()
    updated_user = {**_USER, "display_name": "Sharruk S"}

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "update users" in sql:
            return MockResult([updated_user])
        if "from users" in sql:
            return MockResult([updated_user])
        if "count(*)" in sql and "from submissions" in sql:
            return MockResult([("approved", 6)])
        return MockResult([])

    mock_db.execute.side_effect = _exec

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _USER

    try:
        res = client.patch(
            "/api/v1/users/me",
            json={"display_name": "Sharruk S"},
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["display_name"] == "Sharruk S"
    finally:
        app.dependency_overrides.clear()


def test_update_display_name_validation(client):
    """Validation fails on too short name or invalid characters."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _USER

    try:
        # Too short
        res = client.patch(
            "/api/v1/users/me",
            json={"display_name": "A"},
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()
