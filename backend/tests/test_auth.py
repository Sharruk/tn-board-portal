"""
Tests for get_current_user() authentication dependency.

Covers:
  - Existing user returned from Supabase (happy path)
  - New user auto-created on first login (no .insert().select() chaining)
  - Insert returns empty data -> fallback SELECT retrieves user
  - Insert raises exception (duplicate firebase_uid race condition) -> fallback SELECT
  - Disabled user account -> 403
  - Missing / invalid Authorization header -> 401
  - POST /api/v1/submissions does not fail auth for a first-time user
  - GET  /api/v1/submissions?status=pending does not fail auth for any user

All Supabase and Firebase calls are fully mocked.
No real database connection is required.
"""

import io
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.supabase_client import get_supabase_admin_client
from app.dependencies.auth import get_current_user
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


# -- Helpers -------------------------------------------------------------------

def _make_execute_response(data):
    resp = MagicMock()
    resp.data = data
    return resp


def _make_admin_db_for_existing_user():
    mock_db = MagicMock()
    select_response = _make_execute_response([_EXISTING_USER])

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.return_value = select_response

    mock_db.table.return_value = query
    return mock_db


def _make_admin_db_for_new_user_insert_returns_data():
    mock_db = MagicMock()

    select_empty = _make_execute_response([])
    insert_response = _make_execute_response([_CREATED_USER])

    insert_builder = MagicMock()
    insert_builder.execute.return_value = insert_response

    call_count = {"n": 0}
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query

    def execute_side_effect():
        call_count["n"] += 1
        if call_count["n"] == 1:
            return select_empty
        return _make_execute_response([])

    query.execute.side_effect = execute_side_effect
    query.insert.return_value = insert_builder

    mock_db.table.return_value = query
    return mock_db


def _make_admin_db_for_new_user_insert_empty_fallback():
    mock_db = MagicMock()

    select_empty = _make_execute_response([])
    insert_empty = _make_execute_response([])
    fallback_response = _make_execute_response([_CREATED_USER])

    insert_builder = MagicMock()
    insert_builder.execute.return_value = insert_empty

    select_call_count = {"n": 0}
    select_query = MagicMock()
    select_query.select.return_value = select_query
    select_query.eq.return_value = select_query

    def select_execute():
        select_call_count["n"] += 1
        if select_call_count["n"] == 1:
            return select_empty
        return fallback_response

    select_query.execute.side_effect = select_execute
    select_query.insert.return_value = insert_builder

    mock_db.table.return_value = select_query
    return mock_db


def _make_admin_db_for_race_condition():
    mock_db = MagicMock()

    select_empty = _make_execute_response([])
    fallback_response = _make_execute_response([_CREATED_USER])

    insert_builder = MagicMock()
    insert_builder.execute.side_effect = Exception(
        'duplicate key value violates unique constraint "users_firebase_uid_key"'
    )

    select_call_count = {"n": 0}
    select_query = MagicMock()
    select_query.select.return_value = select_query
    select_query.eq.return_value = select_query

    def select_execute():
        select_call_count["n"] += 1
        if select_call_count["n"] == 1:
            return select_empty
        return fallback_response

    select_query.execute.side_effect = select_execute
    select_query.insert.return_value = insert_builder

    mock_db.table.return_value = select_query
    return mock_db


def _make_admin_db_disabled_user():
    mock_db = MagicMock()
    disabled_user = {**_EXISTING_USER, "is_active": False}
    select_response = _make_execute_response([disabled_user])

    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.execute.return_value = select_response

    mock_db.table.return_value = query
    return mock_db


def _make_submission_admin_db():
    mock_db = MagicMock()

    def table_side_effect(name):
        if name == "submissions":
            data = [_MOCK_SUBMISSION]
        elif name == "submission_files":
            data = [_MOCK_FILE]
        else:
            data = []
        resp = _make_execute_response(data)
        query = MagicMock()
        query.select.return_value = query
        query.insert.return_value = query
        query.eq.return_value = query
        query.in_.return_value = query
        query.or_.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute.return_value = resp
        return query

    mock_db.table.side_effect = table_side_effect
    mock_db.storage = MagicMock()
    bucket = MagicMock()
    bucket.upload.return_value = MagicMock()
    mock_db.storage.from_.return_value = bucket
    return mock_db


from app.dependencies.auth import get_current_user as _get_current_user


# -- Tests: existing user ------------------------------------------------------


class TestGetCurrentUserExistingUser:

    def test_existing_user_returned_without_insert(self):
        """Existing firebase_uid -> user dict returned, insert NOT called."""
        mock_db = _make_admin_db_for_existing_user()
        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_USER,
                admin_db=mock_db,
            )
        )
        assert result == _EXISTING_USER
        mock_db.table.return_value.insert.assert_not_called()

    def test_existing_user_endpoint_returns_200(self):
        """Via FastAPI TestClient: admin endpoint succeeds for an existing admin user."""
        mock_db = _make_submission_admin_db()
        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        # The submissions list endpoint requires ADMIN role; override accordingly.
        app.dependency_overrides[get_current_user] = lambda: {
            **_EXISTING_USER,
            "role": "ADMIN",
        }
        client = TestClient(app)
        response = client.get(
            "/api/v1/submissions",
            headers={"Authorization": "Bearer valid-token"},
        )
        app.dependency_overrides.clear()
        assert response.status_code == 200


# -- Tests: new user (first login) ---------------------------------------------


class TestGetCurrentUserNewUser:

    def test_new_user_created_insert_returns_data(self):
        """First login: SELECT empty -> insert -> row returned directly."""
        mock_db = _make_admin_db_for_new_user_insert_returns_data()
        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_USER,
                admin_db=mock_db,
            )
        )
        assert result["firebase_uid"] == _FIREBASE_UID
        assert result["role"] == "USER"

        insert_call_args = mock_db.table.return_value.insert.call_args[0][0]
        assert insert_call_args["firebase_uid"] == _FIREBASE_UID
        assert insert_call_args["email"] == _EMAIL
        assert insert_call_args["role"] == "USER"
        assert insert_call_args["is_active"] is True

    def test_super_admin_email_gets_super_admin_role(self):
        """Designated super admin email receives SUPER_ADMIN role on first login."""
        created_admin = {
            **_CREATED_USER,
            "firebase_uid": "admin-firebase-uid",
            "email": _ADMIN_EMAIL,
            "role": "SUPER_ADMIN",
        }
        mock_db = MagicMock()
        select_empty = _make_execute_response([])
        insert_response = _make_execute_response([created_admin])

        insert_builder = MagicMock()
        insert_builder.execute.return_value = insert_response

        query = MagicMock()
        query.select.return_value = query
        query.eq.return_value = query
        query.execute.return_value = select_empty
        query.insert.return_value = insert_builder
        mock_db.table.return_value = query

        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_SUPER_ADMIN,
                admin_db=mock_db,
            )
        )
        assert result["role"] == "SUPER_ADMIN"
        insert_args = mock_db.table.return_value.insert.call_args[0][0]
        assert insert_args["role"] == "SUPER_ADMIN"

    def test_insert_no_select_chain(self):
        """
        Regression guard: .insert(...).select(...) must NOT be called.
        The insert builder's .select attribute must never be invoked.
        """
        mock_db = _make_admin_db_for_new_user_insert_returns_data()
        asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_USER,
                admin_db=mock_db,
            )
        )
        insert_builder = mock_db.table.return_value.insert.return_value
        insert_builder.select.assert_not_called()

    def test_fallback_select_when_insert_returns_empty(self):
        """Insert returns no rows -> fallback SELECT retrieves the created user."""
        mock_db = _make_admin_db_for_new_user_insert_empty_fallback()
        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_USER,
                admin_db=mock_db,
            )
        )
        assert result["firebase_uid"] == _FIREBASE_UID


# -- Tests: race condition ------------------------------------------------------


class TestGetCurrentUserRaceCondition:

    def test_duplicate_uid_exception_falls_back_to_select(self):
        """
        Insert raises a duplicate-key exception (concurrent request won) ->
        fallback SELECT returns the user created by the concurrent request.
        """
        mock_db = _make_admin_db_for_race_condition()
        result = asyncio.run(
            _get_current_user(
                decoded_token=_DECODED_TOKEN_USER,
                admin_db=mock_db,
            )
        )
        assert result["firebase_uid"] == _FIREBASE_UID
        mock_db.table.return_value.insert.assert_called_once()


# -- Tests: disabled account ---------------------------------------------------


class TestGetCurrentUserDisabledAccount:

    def test_disabled_user_raises_403(self):
        from fastapi import HTTPException

        mock_db = _make_admin_db_disabled_user()
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                _get_current_user(
                    decoded_token=_DECODED_TOKEN_USER,
                    admin_db=mock_db,
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

    def test_post_submission_first_time_user_no_500(self):
        """POST /api/v1/submissions must not return 500 for a first-time user."""
        mock_db = _make_submission_admin_db()

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {
            "role": "USER",
            "email": _EMAIL,
            "firebase_uid": _FIREBASE_UID,
        }

        client = TestClient(app)
        response = client.post(
            "/api/v1/submissions",
            data={
                "publisher_name": "First Timer",
                "email": _EMAIL,
                "details": "A paper",
            },
            files=[("files", ("test.pdf", io.BytesIO(b"PDF content"), "application/pdf"))],
        )
        app.dependency_overrides.clear()
        assert response.status_code != 500

    def test_get_admin_submissions_pending_no_500(self):
        """GET /api/v1/submissions?limit=50&status=pending must not return 500."""
        mock_db = _make_submission_admin_db()

        app.dependency_overrides[get_supabase_admin_client] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: {
            "role": "ADMIN",
            "email": "admin@example.com",
            "firebase_uid": "admin-uid",
        }

        client = TestClient(app)
        response = client.get(
            "/api/v1/submissions?limit=50&status=pending",
            headers={"Authorization": "Bearer valid-admin-token"},
        )
        app.dependency_overrides.clear()
        assert response.status_code != 500
        assert response.status_code == 200
