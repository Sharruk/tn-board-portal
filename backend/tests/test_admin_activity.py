"""
Unit and integration tests for Central Admin Activity Logs:
  - GET /api/v1/admin/activity-logs
  - AdminActivityRepository write and read methods
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.dependencies.supabase import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.main import app
from app.repositories.admin_activity_repository import AdminActivityRepository
from app.services.admin_activity_service import AdminActivityService


class MockRow:
    def __init__(self, data: dict):
        self._mapping = data

    def __getitem__(self, key):
        return self._mapping[key]


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


_NOW = datetime.now(timezone.utc)

_SAMPLE_LOG = {
    "id": "11111111-1111-1111-1111-111111111111",
    "actor_uid": "admin-uid-1",
    "actor_email": "admin1@example.com",
    "actor_name": "Admin One",
    "actor_role": "ADMIN",
    "action": "submission.approve",
    "target_type": "submission",
    "target_id": "sub-100",
    "target_title": "Class 10 Maths Paper",
    "reason": None,
    "metadata": {"created_paper_ids": [42]},
    "ip_address": "127.0.0.1",
    "created_at": _NOW,
}

_SAMPLE_SUPER_LOG = {
    "id": "22222222-2222-2222-2222-222222222222",
    "actor_uid": "super-uid-1",
    "actor_email": "superadmin@example.com",
    "actor_name": "Super Admin",
    "actor_role": "SUPER_ADMIN",
    "action": "admin.promote_user",
    "target_type": "user",
    "target_id": "user-200",
    "target_title": "Riyaz",
    "reason": "Promoted to math coordinator",
    "metadata": {"previous_role": "USER", "new_role": "ADMIN"},
    "ip_address": "192.168.1.1",
    "created_at": _NOW - timedelta(minutes=10),
}

_ADMIN = {
    "id": "admin-uid-1",
    "firebase_uid": "admin-uid-1",
    "email": "admin1@example.com",
    "display_name": "Admin One",
    "role": "ADMIN",
    "is_active": True,
}

_SUPER_ADMIN = {
    "id": "super-uid-1",
    "firebase_uid": "super-uid-1",
    "email": "superadmin@example.com",
    "display_name": "Super Admin",
    "role": "SUPER_ADMIN",
    "is_active": True,
}

_USER = {
    "id": "user-uid-1",
    "firebase_uid": "user-uid-1",
    "email": "student@example.com",
    "display_name": "Student",
    "role": "USER",
    "is_active": True,
}

_CONTRIBUTOR = {
    "id": "contrib-uid-1",
    "firebase_uid": "contrib-uid-1",
    "email": "teacher@example.com",
    "display_name": "Teacher Contributor",
    "role": "CONTRIBUTOR",
    "is_active": True,
}


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. Authorization Tests ───────────────────────────────────────────────────

def test_admin_can_view_activity_logs(client):
    """Active Admin can retrieve activity logs."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = [
        MockResult(scalar_val=1),  # count
        MockResult([_SAMPLE_LOG]),  # rows
    ]
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer token"})
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert len(body["data"]) == 1
        assert body["data"][0]["actor_uid"] == "admin-uid-1"
        assert body["data"][0]["action"] == "submission.approve"
    finally:
        app.dependency_overrides.clear()


def test_super_admin_can_view_activity_logs(client):
    """Active Super Admin can retrieve activity logs."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = [
        MockResult(scalar_val=2),  # count
        MockResult([_SAMPLE_LOG, _SAMPLE_SUPER_LOG]),  # rows
    ]
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.get("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer token"})
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        assert len(body["data"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_ordinary_user_cannot_view_activity_logs(client):
    """Ordinary student user receives 403 Forbidden."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _USER

    try:
        res = client.get("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer token"})
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_contributor_cannot_view_activity_logs(client):
    """Contributor user receives 403 Forbidden."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: _CONTRIBUTOR

    try:
        res = client.get("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer token"})
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_disabled_admin_cannot_view_activity_logs(client):
    """Disabled account receives 403 Forbidden."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    def _raise_disabled():
        raise HTTPException(status_code=403, detail="Account is disabled.")

    app.dependency_overrides[get_current_user] = _raise_disabled

    try:
        res = client.get("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer token"})
        assert res.status_code == 403
        assert "Account is disabled" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_revoked_admin_cannot_view_activity_logs(client):
    """Revoked Admin (demoted back to USER) receives 403 Forbidden."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    demoted_user = {**_ADMIN, "role": "USER"}
    app.dependency_overrides[get_current_user] = lambda: demoted_user

    try:
        res = client.get("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer token"})
        assert res.status_code == 403
        assert "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_request_rejected(client):
    """Request without Bearer token receives 401 Unauthorized."""
    res = client.get("/api/v1/admin/activity-logs")
    assert res.status_code == 401


# ── 2. Filtering & Parameter Validation Tests ─────────────────────────────────

def test_filter_by_actor_uid(client):
    """Filtering by actor_uid passes query parameter to repository."""
    mock_db = MagicMock()
    captured_queries = []

    def _exec(stmt, params=None):
        captured_queries.append((str(stmt).lower(), params or {}))
        if "count(*)" in str(stmt).lower():
            return MockResult(scalar_val=1)
        return MockResult([_SAMPLE_LOG])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get(
            "/api/v1/admin/activity-logs?actor_uid=admin-uid-1",
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 200
        # Check that WHERE actor_uid = :actor_uid was in SQL
        count_sql, count_p = captured_queries[0]
        assert "actor_uid = :actor_uid" in count_sql
        assert count_p["actor_uid"] == "admin-uid-1"

        data_sql, data_p = captured_queries[1]
        assert "actor_uid = :actor_uid" in data_sql
        assert data_p["actor_uid"] == "admin-uid-1"
    finally:
        app.dependency_overrides.clear()


def test_filter_by_action(client):
    """Filtering by action passes parameter to repository."""
    mock_db = MagicMock()
    captured_queries = []

    def _exec(stmt, params=None):
        captured_queries.append((str(stmt).lower(), params or {}))
        if "count(*)" in str(stmt).lower():
            return MockResult(scalar_val=1)
        return MockResult([_SAMPLE_SUPER_LOG])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.get(
            "/api/v1/admin/activity-logs?action=admin.promote_user",
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 200
        data_sql, data_p = captured_queries[1]
        assert "action = :action" in data_sql
        assert data_p["action"] == "admin.promote_user"
    finally:
        app.dependency_overrides.clear()


def test_filter_by_date_range(client):
    """Filtering with valid start_date and end_date."""
    mock_db = MagicMock()
    captured_queries = []

    def _exec(stmt, params=None):
        captured_queries.append((str(stmt).lower(), params or {}))
        if "count(*)" in str(stmt).lower():
            return MockResult(scalar_val=1)
        return MockResult([_SAMPLE_LOG])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get(
            "/api/v1/admin/activity-logs?start_date=2026-01-01T00:00:00Z&end_date=2026-12-31T23:59:59Z",
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 200
        data_sql, data_p = captured_queries[1]
        assert "created_at >= :start_date" in data_sql
        assert "created_at <= :end_date" in data_sql
    finally:
        app.dependency_overrides.clear()


def test_invalid_date_range_rejected(client):
    """When start_date is later than end_date, returns 422 Unprocessable Entity."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get(
            "/api/v1/admin/activity-logs?start_date=2026-12-31T23:59:59Z&end_date=2026-01-01T00:00:00Z",
            headers={"Authorization": "Bearer token"},
        )
        assert res.status_code == 422
        assert "start_date cannot be later than end_date" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_invalid_pagination_parameters(client):
    """limit > 100 or limit < 1 or offset < 0 rejected by FastAPI validator."""
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        # limit too high
        res1 = client.get("/api/v1/admin/activity-logs?limit=101", headers={"Authorization": "Bearer token"})
        assert res1.status_code == 422

        # limit too low
        res2 = client.get("/api/v1/admin/activity-logs?limit=0", headers={"Authorization": "Bearer token"})
        assert res2.status_code == 422

        # negative offset
        res3 = client.get("/api/v1/admin/activity-logs?offset=-5", headers={"Authorization": "Bearer token"})
        assert res3.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ── 3. Deterministic Ordering Tests ──────────────────────────────────────────

def test_deterministic_ordering_newest_first(client):
    """Query includes ORDER BY created_at DESC, id DESC."""
    mock_db = MagicMock()
    captured_queries = []

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        captured_queries.append(sql)
        if "count(*)" in sql:
            return MockResult(scalar_val=2)
        return MockResult([_SAMPLE_LOG, _SAMPLE_SUPER_LOG])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: _ADMIN

    try:
        res = client.get("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer token"})
        assert res.status_code == 200
        data_sql = captured_queries[1]
        assert "order by created_at desc, id desc" in data_sql
    finally:
        app.dependency_overrides.clear()


# ── 4. Immutability / Method Not Allowed Tests ────────────────────────────────

def test_mutation_endpoints_not_allowed(client):
    """Activity logs endpoint has no write, update or delete endpoints."""
    app.dependency_overrides[require_admin] = lambda: _SUPER_ADMIN

    try:
        # POST on collection is 405 Method Not Allowed
        post_res = client.post("/api/v1/admin/activity-logs", json={"action": "test"}, headers={"Authorization": "Bearer t"})
        assert post_res.status_code == 405

        # PUT on collection is 405 Method Not Allowed
        put_col_res = client.put("/api/v1/admin/activity-logs", json={"reason": "edit"}, headers={"Authorization": "Bearer t"})
        assert put_col_res.status_code == 405

        # DELETE on collection is 405 Method Not Allowed
        del_col_res = client.delete("/api/v1/admin/activity-logs", headers={"Authorization": "Bearer t"})
        assert del_col_res.status_code == 405

        # Sub-routes (/some-id) do not exist at all (404)
        put_res = client.put("/api/v1/admin/activity-logs/some-id", json={"reason": "edit"}, headers={"Authorization": "Bearer t"})
        assert put_res.status_code == 404

        del_res = client.delete("/api/v1/admin/activity-logs/some-id", headers={"Authorization": "Bearer t"})
        assert del_res.status_code == 404
    finally:
        app.dependency_overrides.clear()


# ── 5. Repository Transaction & Validation Invariant Tests ───────────────────

def test_log_activity_enlists_in_transaction_without_independent_commit():
    """
    Architectural Invariant:
    log_activity() must execute within the caller's active session and must NOT
    call commit() independently, leaving transaction control with the caller.
    """
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([_SAMPLE_LOG])
    repo = AdminActivityRepository(mock_db)

    result = repo.log_activity(
        actor_uid="admin-uid-1",
        actor_email="admin1@example.com",
        actor_name="Admin One",
        actor_role="ADMIN",
        action="submission.approve",
        target_type="submission",
        target_id="sub-100",
        target_title="Class 10 Maths Paper",
        reason=None,
        metadata={"created_paper_ids": [42]},
        ip_address="127.0.0.1",
    )

    assert result["id"] == "11111111-1111-1111-1111-111111111111"
    # execute was called with SQL statement
    assert mock_db.execute.called
    # commit() was NOT called by repository!
    assert not mock_db.commit.called
    # rollback() was NOT called by repository!
    assert not mock_db.rollback.called


def test_log_activity_validates_required_fields():
    """Missing or empty required fields raise ValueError before SQL execution."""
    mock_db = MagicMock()
    repo = AdminActivityRepository(mock_db)

    # Missing actor_uid
    with pytest.raises(ValueError, match="actor_uid is required"):
        repo.log_activity(
            actor_uid="",
            actor_email="a@b.com",
            actor_name="Name",
            actor_role="ADMIN",
            action="action",
            target_type="type",
            target_id="1",
        )

    # Missing action
    with pytest.raises(ValueError, match="action is required"):
        repo.log_activity(
            actor_uid="uid",
            actor_email="a@b.com",
            actor_name="Name",
            actor_role="ADMIN",
            action="   ",
            target_type="type",
            target_id="1",
        )

    # Missing target_type
    with pytest.raises(ValueError, match="target_type is required"):
        repo.log_activity(
            actor_uid="uid",
            actor_email="a@b.com",
            actor_name="Name",
            actor_role="ADMIN",
            action="action",
            target_type="",
            target_id="1",
        )

    # Ensure no database statement was executed
    assert not mock_db.execute.called


def test_log_activity_failure_propagates_to_caller():
    """If database insert fails, log_activity does not swallow the exception."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = RuntimeError("PostgreSQL constraint error")
    repo = AdminActivityRepository(mock_db)

    with pytest.raises(RuntimeError, match="PostgreSQL constraint error"):
        repo.log_activity(
            actor_uid="uid-1",
            actor_email="admin@example.com",
            actor_name="Admin",
            actor_role="ADMIN",
            action="action",
            target_type="user",
            target_id="target-1",
        )
