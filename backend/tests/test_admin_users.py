"""
Tests for Admin User Management endpoints:
  - GET /api/v1/admin/users
  - GET /api/v1/admin/users/{firebase_uid}
"""

from datetime import datetime
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.dependencies.auth import require_admin
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


_ADMIN = {
    "id": "99999999-9999-9999-9999-999999999999",
    "firebase_uid": "admin-uid-786",
    "email": "hungrylearner786@gmail.com",
    "display_name": "Admin",
    "role": "SUPER_ADMIN",
    "is_active": True,
    "photo_url": "https://example.com/admin.jpg",
}

_USER_ROW = {
    "id": "11111111-1111-1111-1111-111111111111",
    "firebase_uid": "user-uid-123",
    "email": "sharruk@example.com",
    "display_name": "Sharruk S",
    "photo_url": "https://lh3.googleusercontent.com/photo.jpg",
    "role": "USER",
    "is_active": True,
    "created_at": datetime.now(),
    "last_active_at": datetime.now(),
    "total_submissions": 5,
    "published_count": 4,
    "pending_count": 1,
    "rejected_count": 0,
}


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_users_unauthenticated(client):
    """Unauthenticated call returns 401."""
    res = client.get("/api/v1/admin/users")
    assert res.status_code == 401


def test_admin_users_list_success(client):
    """Admin can fetch paginated user list."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "total_users" in sql:
            return MockResult([{"total_users": 10, "total_contributors": 4}])
        if "select count(*) from users" in sql:
            return MockResult(scalar_val=1)
        if "from users u" in sql or "from users" in sql:
            return MockResult([_USER_ROW])
        if "from submissions" in sql:
            return MockResult([])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get("/api/v1/admin/users", headers={"Authorization": "Bearer admin-token"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["total_registered_users"] == 10
        assert data["total_contributors"] == 4
        assert len(data["data"]) == 1
        u = data["data"][0]
        assert u["email"] == "sharruk@example.com"
        assert u["display_name"] == "Sharruk S"
        assert u["total_submissions"] == 5
        assert u["published_count"] == 4
    finally:
        app.dependency_overrides.clear()


def test_admin_user_detail_success(client):
    """Admin can fetch complete user detail with submissions and conversations."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "from users" in sql:
            return MockResult([_USER_ROW])
        if "from submissions" in sql and "where s.firebase_uid" in sql:
            return MockResult([
                {
                    "id": "55555555-5555-5555-5555-555555555555",
                    "publisher_name": "Sharruk S",
                    "details": "Maths Paper",
                    "status": "approved",
                    "rejection_reason": None,
                    "thank_you_message": "Thank you!",
                    "created_at": datetime.now(),
                    "reviewed_at": datetime.now(),
                    "file_count": 2,
                }
            ])
        if "from papers where submission_id" in sql:
            return MockResult([{"id": 101, "title": "Class 10 Maths", "year": 2024, "exam_type": "Quarterly"}])
        if "from conversations" in sql:
            return MockResult([
                {
                    "id": "66666666-6666-6666-6666-666666666666",
                    "category": "feedback",
                    "subject": "Great portal!",
                    "status": "resolved",
                    "unread_count": 0,
                    "last_message": "Thanks!",
                    "updated_at": datetime.now(),
                    "created_at": datetime.now(),
                }
            ])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get(
            f"/api/v1/admin/users/{_USER_ROW['firebase_uid']}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["user"]["display_name"] == "Sharruk S"
        assert len(data["submissions"]) == 1
        assert data["submissions"][0]["status"] == "approved"
        assert len(data["conversations"]) == 1
        assert data["conversations"][0]["category"] == "feedback"
    finally:
        app.dependency_overrides.clear()


def test_admin_user_detail_not_found(client):
    """Admin requesting nonexistent user returns 404."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get(
            "/api/v1/admin/users/nonexistent-uid",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()
