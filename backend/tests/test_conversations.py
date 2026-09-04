"""
Tests for Student Conversations and Admin Inbox endpoints:
  - POST /api/v1/conversations
  - GET /api/v1/conversations/me
  - GET /api/v1/conversations/unread-count
  - GET /api/v1/conversations/{id}
  - POST /api/v1/conversations/{id}/messages
  - GET /api/v1/admin/conversations
  - GET /api/v1/admin/conversations/stats
  - GET /api/v1/admin/conversations/{id}
  - POST /api/v1/admin/conversations/{id}/reply
  - PATCH /api/v1/admin/conversations/{id}/status
"""

from datetime import datetime
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.dependencies.auth import get_current_user, require_admin
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
    def __init__(self, rows: list[dict | tuple] | None = None, scalar_val=None, rowcount=1):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


_STUDENT = {
    "id": "11111111-1111-1111-1111-111111111111",
    "firebase_uid": "student-uid-123",
    "email": "student@example.com",
    "display_name": "Student A",
    "role": "USER",
    "is_active": True,
    "photo_url": "https://example.com/student.jpg",
}

_OTHER_STUDENT = {
    "id": "22222222-2222-2222-2222-222222222222",
    "firebase_uid": "other-uid-456",
    "email": "other@example.com",
    "display_name": "Other Student",
    "role": "USER",
    "is_active": True,
    "photo_url": None,
}

_ADMIN = {
    "id": "99999999-9999-9999-9999-999999999999",
    "firebase_uid": "admin-uid-786",
    "email": "hungrylearner786@gmail.com",
    "display_name": "Admin",
    "role": "SUPER_ADMIN",
    "is_active": True,
    "photo_url": "https://example.com/admin.jpg",
}

_CONV = {
    "id": "33333333-3333-3333-3333-333333333333",
    "firebase_uid": "student-uid-123",
    "user_email": "student@example.com",
    "user_display_name": "Student A",
    "category": "material_request",
    "subject": "Class 10 Maths Quarterly 2025",
    "status": "awaiting_admin",
    "submission_id": None,
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    "user_photo_url": "https://example.com/student.jpg",
    "unread_count": 0,
    "last_message": "Please upload this paper",
    "last_message_at": datetime.now(),
    "last_message_sender_role": "user",
}

_MSG = {
    "id": "44444444-4444-4444-4444-444444444444",
    "conversation_id": "33333333-3333-3333-3333-333333333333",
    "sender_role": "user",
    "sender_firebase_uid": "student-uid-123",
    "sender_name": "Student A",
    "message": "Please upload this paper",
    "is_read": False,
    "read_at": None,
    "created_at": datetime.now(),
}


@pytest.fixture
def client():
    return TestClient(app)


def test_create_conversation_unauthenticated(client):
    """Unauthenticated call returns 401."""
    res = client.post("/api/v1/conversations", json={"category": "general_question", "subject": "Test", "message": "Help"})
    assert res.status_code == 401


def test_create_conversation_success(client):
    """Student can start a new support conversation."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into conversations" in sql:
            return MockResult([_CONV])
        if "insert into messages" in sql:
            return MockResult([_MSG])
        if "from conversations" in sql:
            return MockResult([_CONV])
        if "from messages" in sql:
            return MockResult([_MSG])
        if "update messages" in sql:
            return MockResult([], rowcount=0)
        return MockResult([])

    mock_db.execute.side_effect = _exec

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _STUDENT

    try:
        res = client.post(
            "/api/v1/conversations",
            json={
                "category": "material_request",
                "subject": "Class 10 Maths Quarterly 2025",
                "message": "Please upload this paper",
            },
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["subject"] == "Class 10 Maths Quarterly 2025"
        assert data["category"] == "material_request"
        assert len(data["messages"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_create_conversation_invalid_category(client):
    """Fails with 422 if invalid category provided."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _STUDENT

    try:
        res = client.post(
            "/api/v1/conversations",
            json={
                "category": "not_a_valid_category",
                "subject": "Class 10 Maths",
                "message": "Hello",
            },
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_get_my_conversations(client):
    """Student can list their own conversations."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "select count(*) from conversations where" in sql:
            return MockResult(scalar_val=1)
        if "from conversations" in sql:
            return MockResult([_CONV])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _STUDENT

    try:
        res = client.get("/api/v1/conversations/me", headers={"Authorization": "Bearer token"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["data"][0]["subject"] == "Class 10 Maths Quarterly 2025"
    finally:
        app.dependency_overrides.clear()


def test_student_cannot_access_other_user_conversation(client):
    """Student A cannot access Student B's conversation (isolation enforced)."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "from conversations" in sql:
            return MockResult([_CONV])  # Owned by student-uid-123
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _OTHER_STUDENT  # other-uid-456

    try:
        res = client.get(
            f"/api/v1/conversations/{_CONV['id']}",
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_admin_conversations_access(client):
    """Admin can list conversations and fetch stats."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "as total" in sql or "filter" in sql:
            return MockResult([{"total": 5, "unread_count": 2, "awaiting_admin": 3, "awaiting_user": 1, "resolved": 1}])
        if "select count(*) from conversations c" in sql:
            return MockResult(scalar_val=1)
        if "from conversations" in sql:
            return MockResult([_CONV])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        # List
        res = client.get("/api/v1/admin/conversations", headers={"Authorization": "Bearer admin-token"})
        assert res.status_code == 200
        assert res.json()["total"] == 1

        # Stats
        res_stats = client.get("/api/v1/admin/conversations/stats", headers={"Authorization": "Bearer admin-token"})
        assert res_stats.status_code == 200
        assert res_stats.json()["total"] == 5
        assert res_stats.json()["unread_count"] == 2
    finally:
        app.dependency_overrides.clear()


def test_admin_reply_and_resolve(client):
    """Admin can reply to a conversation and mark it resolved."""
    mock_db = MagicMock()
    reply_msg = {**_MSG, "sender_role": "admin", "sender_name": "TN Board Admin", "message": "Uploaded!"}
    resolved_conv = {**_CONV, "status": "resolved"}

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "from conversations" in sql:
            return MockResult([resolved_conv])
        if "from messages" in sql:
            return MockResult([_MSG, reply_msg])
        if "insert into messages" in sql:
            return MockResult([reply_msg])
        if "update conversations" in sql:
            return MockResult([resolved_conv])
        if "from users" in sql:
            return MockResult([_STUDENT])
        if "from submissions" in sql:
            return MockResult([("approved", 2)])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        # Reply
        res = client.post(
            f"/api/v1/admin/conversations/{_CONV['id']}/reply",
            json={"message": "Uploaded!"},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 201
        assert res.json()["sender_role"] == "admin"

        # Resolve status
        res_status = client.patch(
            f"/api/v1/admin/conversations/{_CONV['id']}/status",
            json={"status": "resolved"},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res_status.status_code == 200
        assert res_status.json()["status"] == "resolved"
    finally:
        app.dependency_overrides.clear()
