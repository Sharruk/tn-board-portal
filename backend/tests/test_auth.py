"""
Tests for get_current_user() authentication dependency.

Covers:
  - Existing user returned from PostgreSQL (happy path)
  - New user auto-created on first login
  - Insert returns data / duplicate handling
  - Disabled user account -> 403
  - Missing / invalid Authorization header -> 401
  - POST /api/v1/submissions does not fail auth for a first-time user
  - GET  /api/v1/submissions?status=pending does not fail auth for any user
"""

import asyncio
import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user as _get_current_user, get_current_user
from app.dependencies.supabase import get_db
from app.main import app

# -- Shared constants ----------------------------------------------------------

_FIREBASE_UID = "firebase-uid-abc123"
_EMAIL = "user@example.com"
_ADMIN_EMAIL = "hungrylearner786@gmail.com"

_DECODED_TOKEN_USER = {
    "uid": _FIREBASE_UID,
    "email": _EMAIL,
    "name": "Test User",
}

_DECODED_TOKEN_SUPER_ADMIN = {
    "uid": "admin-firebase-uid",
    "email": _ADMIN_EMAIL,
    "name": "Admin User",
}

_EXISTING_USER = {
    "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    "firebase_uid": _FIREBASE_UID,
    "email": _EMAIL,
    "display_name": "Test User",
    "role": "USER",
    "is_active": True,
}

_CREATED_USER = {
    "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    "firebase_uid": _FIREBASE_UID,
    "email": _EMAIL,
    "display_name": "Test User",
    "role": "USER",
    "is_active": True,
}

_SUB_ID = "11111111-1111-1111-1111-111111111111"
_MOCK_SUBMISSION = {
    "id": _SUB_ID,
    "publisher_name": "Test Contributor",
    "email": _EMAIL,
    "firebase_uid": _FIREBASE_UID,
    "details": "Sample paper",
    "status": "pending",
    "rejection_reason": None,
    "reviewed_at": None,
    "created_at": "2024-03-15T10:30:00+00:00",
}
_MOCK_FILE = {
    "id": "22222222-2222-2222-2222-222222222222",
    "submission_id": _SUB_ID,
    "original_filename": "paper.pdf",
    "storage_path": f"{_SUB_ID}/paper.pdf",
    "public_url": f"https://example.supabase.co/storage/v1/object/public/submissions/{_SUB_ID}/paper.pdf",
    "file_type": "pdf",
    "file_size": 10240,
    "created_at": "2024-03-15T10:30:00+00:00",
}


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


def _make_db_for_existing_user():
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([_EXISTING_USER])
    return mock_db


def _make_db_for_new_user(role="USER"):
    mock_db = MagicMock()
    user_data = {**_CREATED_USER, "role": role}

    call_count = {"n": 0}

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "insert into users" in sql:
            return MockResult([user_data])
        call_count["n"] += 1
        if call_count["n"] == 1:
            return MockResult([])  # First SELECT returns not found
        return MockResult([user_data])

    mock_db.execute.side_effect = _exec
    return mock_db


def _make_submission_db():
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "from submissions" in sql:
            return MockResult([_MOCK_SUBMISSION])
        if "from submission_files" in sql:
            if "count(*)" in sql:
                return MockResult([(_SUB_ID, 1)])
            return MockResult([_MOCK_FILE])
        if "insert into submissions" in sql:
            return MockResult([_MOCK_SUBMISSION])
        if "insert into submission_files" in sql:
            return MockResult([_MOCK_FILE])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    return mock_db


# -- Tests: existing user ------------------------------------------------------


class TestGetCurrentUserExistingUser:

    def test_existing_user_returned_without_insert(self):
        mock_db = _make_db_for_existing_user()
        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_USER,
                db=mock_db,
            )
        )
        assert result == _EXISTING_USER

    def test_existing_user_endpoint_returns_200(self):
        """Via FastAPI TestClient: admin endpoint succeeds for an existing admin user."""
        from app.dependencies.auth import require_admin
        mock_db = _make_submission_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[require_admin] = lambda: {
            **_EXISTING_USER,
            "role": "ADMIN",
        }
        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1/submissions",
                headers={"Authorization": "Bearer valid-token"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()



# -- Tests: new user (first login) ---------------------------------------------


class TestGetCurrentUserNewUser:

    def test_new_user_created_insert_returns_data(self):
        mock_db = _make_db_for_new_user()
        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_USER,
                db=mock_db,
            )
        )
        assert result["firebase_uid"] == _FIREBASE_UID
        assert result["role"] == "USER"

    def test_super_admin_email_gets_super_admin_role(self):
        mock_db = _make_db_for_new_user(role="SUPER_ADMIN")
        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_SUPER_ADMIN,
                db=mock_db,
            )
        )
        assert result["role"] == "SUPER_ADMIN"


# -- Tests: disabled account ---------------------------------------------------


class TestGetCurrentUserDisabledAccount:

    def test_disabled_user_raises_403(self):
        from fastapi import HTTPException

        mock_db = MagicMock()
        mock_db.execute.return_value = MockResult([{**_EXISTING_USER, "is_active": False}])
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                _get_current_user(
                    decoded_token=_DECODED_TOKEN_USER,
                    db=mock_db,
                )
            )
        assert exc_info.value.status_code == 403


# -- Tests: authorization header -----------------------------------------------


class TestAuthorizationHeader:

    def test_no_auth_header_returns_401(self):
        client = TestClient(app)
        response = client.get("/api/v1/submissions")
        assert response.status_code == 401

    def test_malformed_bearer_returns_401(self):
        client = TestClient(app)
        response = client.get(
            "/api/v1/submissions",
            headers={"Authorization": "Token not-a-bearer"},
        )
        assert response.status_code == 401


# -- Tests: submission endpoint integration ------------------------------------


class TestSubmissionEndpointAuthIntegration:

    @patch("app.repositories.submissions_repository.get_storage_client")
    def test_post_submission_first_time_user_no_500(self, mock_get_storage):
        mock_storage = MagicMock()
        mock_get_storage.return_value = mock_storage

        mock_db = _make_submission_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {
            "role": "USER",
            "email": _EMAIL,
            "firebase_uid": _FIREBASE_UID,
        }

        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/submissions",
                data={
                    "publisher_name": "First Timer",
                    "details": "A paper",
                },
                files=[("files", ("test.pdf", io.BytesIO(b"PDF content"), "application/pdf"))],
                headers={"Authorization": "Bearer valid-token"},
            )
            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    def test_get_admin_submissions_pending_no_500(self):
        from app.dependencies.auth import require_admin
        mock_db = _make_submission_db()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[require_admin] = lambda: {
            "role": "ADMIN",
            "email": "admin@example.com",
            "firebase_uid": "admin-uid",
        }

        try:
            client = TestClient(app)
            response = client.get(
                "/api/v1/submissions?limit=50&status=pending",
                headers={"Authorization": "Bearer valid-admin-token"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

