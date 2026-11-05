"""
Tests for Admin Team Group Chat:
  - GET /api/v1/admin/team-chat/messages
  - POST /api/v1/admin/team-chat/messages

Verifies all 13 security and functional requirements:
  1. Admin can read group messages.
  2. Super Admin can read group messages.
  3. Admin can send a group message.
  4. Super Admin can send a group message.
  5. Ordinary User cannot read messages.
  6. Ordinary User cannot send messages.
  7. Contributor cannot read messages.
  8. Contributor cannot send messages.
  9. Revoked Admin cannot access the chat.
  10. Client-supplied sender identity cannot impersonate another Admin.
  11. Empty messages are rejected.
  12. Overlong messages are rejected.
  13. Message history is returned in the correct chronological order.
"""

from datetime import datetime, timedelta
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


# Test user fixtures
_SUPER_ADMIN = {
    "id": "11111111-1111-1111-1111-111111111111",
    "firebase_uid": "superadmin-uid-123",
    "email": "hungrylearner786@gmail.com",
    "display_name": "HUNGRY LEARNER",
    "role": "SUPER_ADMIN",
    "is_active": True,
}

_ADMIN = {
    "id": "22222222-2222-2222-2222-222222222222",
    "firebase_uid": "admin-uid-456",
    "email": "mr.sharruk@gmail.com",
    "display_name": "Sharruk",
    "role": "ADMIN",
    "is_active": True,
}

_ORDINARY_USER = {
    "id": "33333333-3333-3333-3333-333333333333",
    "firebase_uid": "user-uid-789",
    "email": "student@example.com",
    "display_name": "Student",
    "role": "USER",
    "is_active": True,
}

_CONTRIBUTOR = {
    "id": "44444444-4444-4444-4444-444444444444",
    "firebase_uid": "contrib-uid-101",
    "email": "contributor@example.com",
    "display_name": "Contributor",
    "role": "CONTRIBUTOR",
    "is_active": True,
}

_REVOKED_ADMIN = {
    "id": "55555555-5555-5555-5555-555555555555",
    "firebase_uid": "revoked-uid-202",
    "email": "revoked@example.com",
    "display_name": "Revoked Admin",
    "role": "ADMIN",
    "is_active": False,
}

_NOW = datetime.now()
_SAMPLE_MESSAGES = [
    {
        "id": "msg-1111",
        "sender_firebase_uid": "admin-uid-456",
        "sender_email": "mr.sharruk@gmail.com",
        "sender_name": "Sharruk",
        "sender_role": "ADMIN",
        "message": "Hi everyone. We need to discuss the upcoming question paper uploads.",
        "created_at": _NOW - timedelta(minutes=10),
    },
    {
        "id": "msg-2222",
        "sender_firebase_uid": "superadmin-uid-123",
        "sender_email": "hungrylearner786@gmail.com",
        "sender_name": "Hungry Learner",
        "sender_role": "SUPER_ADMIN",
        "message": "Agreed. Let us coordinate review schedules.",
        "created_at": _NOW - timedelta(minutes=5),
    },
]


@pytest.fixture
def client():
    return TestClient(app)


# ── Requirement 1: Admin can read group messages ────────────────────────────
def test_admin_can_read_group_messages(client):
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=2)
        if "from admin_group_messages" in sql:
            return MockResult(_SAMPLE_MESSAGES)
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer admin-token"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["data"]) == 2
        assert data["data"][0]["sender_name"] == "Sharruk"
        assert data["data"][0]["sender_role"] == "ADMIN"
    finally:
        app.dependency_overrides.clear()


# ── Requirement 2: Super Admin can read group messages ──────────────────────
def test_super_admin_can_read_group_messages(client):
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=2)
        if "from admin_group_messages" in sql:
            return MockResult(_SAMPLE_MESSAGES)
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer sa-token"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["data"][1]["sender_name"] == "Hungry Learner"
        assert data["data"][1]["sender_role"] == "SUPER_ADMIN"
    finally:
        app.dependency_overrides.clear()


# ── Requirement 3: Admin can send a group message ───────────────────────────
def test_admin_can_send_group_message(client):
    mock_db = MagicMock()
    created_msg = {
        "id": "msg-new-admin",
        "sender_firebase_uid": _ADMIN["firebase_uid"],
        "sender_email": _ADMIN["email"],
        "sender_name": "Sharruk",
        "sender_role": "ADMIN",
        "message": "Class 10 maths papers uploaded.",
        "created_at": _NOW,
    }

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into admin_group_messages" in sql:
            return MockResult([created_msg])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.post(
            "/api/v1/admin/team-chat/messages",
            json={"message": "Class 10 maths papers uploaded."},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["sender_name"] == "Sharruk"
        assert data["sender_role"] == "ADMIN"
        assert data["sender_email"] == "mr.sharruk@gmail.com"
        assert data["message"] == "Class 10 maths papers uploaded."
    finally:
        app.dependency_overrides.clear()


# ── Requirement 4: Super Admin can send a group message ─────────────────────
def test_super_admin_can_send_group_message(client):
    mock_db = MagicMock()
    created_msg = {
        "id": "msg-new-sa",
        "sender_firebase_uid": _SUPER_ADMIN["firebase_uid"],
        "sender_email": _SUPER_ADMIN["email"],
        "sender_name": "Hungry Learner",
        "sender_role": "SUPER_ADMIN",
        "message": "Welcome to team chat.",
        "created_at": _NOW,
    }

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into admin_group_messages" in sql:
            return MockResult([created_msg])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.post(
            "/api/v1/admin/team-chat/messages",
            json={"message": "Welcome to team chat."},
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["sender_name"] == "Hungry Learner"
        assert data["sender_role"] == "SUPER_ADMIN"
        assert data["sender_email"] == "hungrylearner786@gmail.com"
    finally:
        app.dependency_overrides.clear()


# ── Requirement 5: Ordinary User cannot read messages ───────────────────────
def test_ordinary_user_cannot_read_messages(client):
    app.dependency_overrides[get_current_user] = lambda: _ORDINARY_USER

    try:
        res = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer user-token"})
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── Requirement 6: Ordinary User cannot send messages ───────────────────────
def test_ordinary_user_cannot_send_messages(client):
    app.dependency_overrides[get_current_user] = lambda: _ORDINARY_USER

    try:
        res = client.post(
            "/api/v1/admin/team-chat/messages",
            json={"message": "Hello?"},
            headers={"Authorization": "Bearer user-token"},
        )
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── Requirement 7: Contributor cannot read messages ─────────────────────────
def test_contributor_cannot_read_messages(client):
    app.dependency_overrides[get_current_user] = lambda: _CONTRIBUTOR

    try:
        res = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer contrib-token"})
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── Requirement 8: Contributor cannot send messages ─────────────────────────
def test_contributor_cannot_send_messages(client):
    app.dependency_overrides[get_current_user] = lambda: _CONTRIBUTOR

    try:
        res = client.post(
            "/api/v1/admin/team-chat/messages",
            json={"message": "Contributor trying to post"},
            headers={"Authorization": "Bearer contrib-token"},
        )
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── Requirement 9: Revoked Admin cannot access the chat ─────────────────────
def test_revoked_admin_cannot_access_chat(client):
    # Case A: Admin role was revoked, reverting back to USER
    revoked_to_user = {**_ADMIN, "role": "USER"}
    app.dependency_overrides[get_current_user] = lambda: revoked_to_user

    try:
        # Cannot read
        res_get = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer revoked-token"})
        assert res_get.status_code == 403
        assert "Insufficient permissions" in res_get.json()["detail"]

        # Cannot send
        res_post = client.post(
            "/api/v1/admin/team-chat/messages",
            json={"message": "I was revoked"},
            headers={"Authorization": "Bearer revoked-token"},
        )
        assert res_post.status_code == 403
        assert "Insufficient permissions" in res_post.json()["detail"]
    finally:
        app.dependency_overrides.clear()

    # Case B: Admin account was disabled (is_active is False)
    from fastapi import HTTPException
    def _disabled_auth():
        raise HTTPException(status_code=403, detail="Account is disabled.")

    app.dependency_overrides[get_current_user] = _disabled_auth

    try:
        res_get2 = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer disabled-token"})
        assert res_get2.status_code == 403
        assert "Account is disabled" in res_get2.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── Requirement 10: Client-supplied identity cannot impersonate another Admin ─
def test_client_cannot_impersonate_sender_identity(client):
    mock_db = MagicMock()
    captured_params = {}

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into admin_group_messages" in sql:
            captured_params.update(params or {})
            return MockResult([{
                "id": "msg-safe",
                "sender_firebase_uid": params["uid"],
                "sender_email": params["email"],
                "sender_name": params["name"],
                "sender_role": params["role"],
                "message": params["message"],
                "created_at": _NOW,
            }])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        # Client tries to impersonate Super Admin and different sender name
        res = client.post(
            "/api/v1/admin/team-chat/messages",
            json={
                "message": "Testing spoofing",
                "sender_name": "Impersonated Super Admin",
                "sender_role": "SUPER_ADMIN",
                "sender_email": "fake@superadmin.com",
                "sender_firebase_uid": "spoofed-uid-999",
            },
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 201
        data = res.json()
        # Verify derived from authenticated _ADMIN, NOT from client payload
        assert data["sender_name"] == "Sharruk"
        assert data["sender_role"] == "ADMIN"
        assert data["sender_email"] == "mr.sharruk@gmail.com"
        assert data["sender_firebase_uid"] == "admin-uid-456"

        assert captured_params["uid"] == "admin-uid-456"
        assert captured_params["email"] == "mr.sharruk@gmail.com"
        assert captured_params["name"] == "Sharruk"
        assert captured_params["role"] == "ADMIN"
    finally:
        app.dependency_overrides.clear()


# ── Requirement 11: Empty messages are rejected ─────────────────────────────
def test_empty_messages_are_rejected(client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        # Empty string
        res1 = client.post("/api/v1/admin/team-chat/messages", json={"message": ""}, headers={"Authorization": "Bearer t"})
        assert res1.status_code in (400, 422)

        # Whitespace-only string
        res2 = client.post("/api/v1/admin/team-chat/messages", json={"message": "   \n\t  "}, headers={"Authorization": "Bearer t"})
        assert res2.status_code in (400, 422)
    finally:
        app.dependency_overrides.clear()


# ── Requirement 12: Overlong messages are rejected ──────────────────────────
def test_overlong_messages_are_rejected(client):
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        overlong = "a" * 5001
        res = client.post("/api/v1/admin/team-chat/messages", json={"message": overlong}, headers={"Authorization": "Bearer t"})
        assert res.status_code in (400, 422)
    finally:
        app.dependency_overrides.clear()


# ── Requirement 13: Message history is returned in correct chronological order
def test_messages_returned_in_chronological_order(client):
    mock_db = MagicMock()
    # Message at T-10m and message at T-5m
    ordered_messages = [
        {
            "id": "msg-earlier",
            "sender_firebase_uid": "admin-1",
            "sender_email": "admin1@example.com",
            "sender_name": "Admin One",
            "sender_role": "ADMIN",
            "message": "First message sent earlier",
            "created_at": _NOW - timedelta(minutes=10),
        },
        {
            "id": "msg-later",
            "sender_firebase_uid": "admin-2",
            "sender_email": "admin2@example.com",
            "sender_name": "Admin Two",
            "sender_role": "ADMIN",
            "message": "Second message sent later",
            "created_at": _NOW - timedelta(minutes=5),
        },
    ]

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=2)
        if "from admin_group_messages" in sql:
            assert "order by created_at asc, id asc" in sql
            return MockResult(ordered_messages)
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer t"})
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 2
        # Verify first item is earlier than second item
        assert datetime.fromisoformat(data[0]["created_at"]) < datetime.fromisoformat(data[1]["created_at"])
        assert data[0]["message"] == "First message sent earlier"
        assert data[1]["message"] == "Second message sent later"
    finally:
        app.dependency_overrides.clear()


def test_deterministic_ordering_with_identical_timestamps(client):
    """When messages share the exact same timestamp, id ASC ensures deterministic ordering."""
    mock_db = MagicMock()
    shared_timestamp = _NOW
    identical_ts_messages = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "sender_firebase_uid": "admin-1",
            "sender_email": "admin1@example.com",
            "sender_name": "Admin One",
            "sender_role": "ADMIN",
            "message": "Tie-breaker message A",
            "created_at": shared_timestamp,
        },
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "sender_firebase_uid": "admin-2",
            "sender_email": "admin2@example.com",
            "sender_name": "Admin Two",
            "sender_role": "ADMIN",
            "message": "Tie-breaker message B",
            "created_at": shared_timestamp,
        },
    ]

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "count(*)" in sql:
            return MockResult(scalar_val=2)
        if "from admin_group_messages" in sql:
            assert "order by created_at asc, id asc" in sql
            return MockResult(identical_ts_messages)
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get("/api/v1/admin/team-chat/messages", headers={"Authorization": "Bearer t"})
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 2
        # Both share the exact same timestamp
        assert data[0]["created_at"] == data[1]["created_at"]
        # id ASC guarantees deterministic secondary sorting
        assert data[0]["id"] < data[1]["id"]
        assert data[0]["message"] == "Tie-breaker message A"
        assert data[1]["message"] == "Tie-breaker message B"
    finally:
        app.dependency_overrides.clear()
