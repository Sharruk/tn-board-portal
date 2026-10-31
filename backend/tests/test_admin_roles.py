"""
Tests for Super Admin & Admin Role Management:
  - GET /api/v1/admin/me
  - GET /api/v1/admin/roles/admins
  - GET /api/v1/admin/roles/pending
  - POST /api/v1/admin/roles/preauthorize
  - DELETE /api/v1/admin/roles/pending/{id}
  - POST /api/v1/admin/roles/promote-user
  - DELETE /api/v1/admin/roles/revoke/{uid}
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user, require_admin, require_super_admin, verify_firebase_token
from app.dependencies.supabase import get_db
from app.main import app

# Mock Results helper
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


_SUPER_ADMIN = {
    "id": "00000000-0000-0000-0000-000000000000",
    "firebase_uid": "superadmin-uid-123",
    "email": "hungrylearner786@gmail.com",
    "display_name": "Hungry Learner",
    "role": "SUPER_ADMIN",
    "is_active": True,
    "photo_url": "https://example.com/sa.jpg",
}

_ORDINARY_ADMIN = {
    "id": "11111111-1111-1111-1111-111111111111",
    "firebase_uid": "admin-uid-456",
    "email": "admin@example.com",
    "display_name": "Teacher John",
    "role": "ADMIN",
    "previous_role": "CONTRIBUTOR",
    "is_active": True,
    "photo_url": "https://example.com/admin.jpg",
}

_REGULAR_USER = {
    "id": "22222222-2222-2222-2222-222222222222",
    "firebase_uid": "user-uid-789",
    "email": "student@example.com",
    "display_name": "Student Sharruk",
    "role": "USER",
    "is_active": True,
    "photo_url": None,
}

_CONTRIBUTOR_USER = {
    "id": "33333333-3333-3333-3333-333333333333",
    "firebase_uid": "contrib-uid-101",
    "email": "contributor@example.com",
    "display_name": "Anand Contributor",
    "role": "CONTRIBUTOR",
    "is_active": True,
    "photo_url": None,
}


@pytest.fixture
def client():
    return TestClient(app)


# ── 1. Unauthenticated Requests ───────────────────────────────────────────────

def test_admin_me_unauthenticated(client):
    res = client.get("/api/v1/admin/me")
    assert res.status_code == 401


def test_list_admins_unauthenticated(client):
    res = client.get("/api/v1/admin/roles/admins")
    assert res.status_code == 401


def test_promote_user_unauthenticated(client):
    res = client.post("/api/v1/admin/roles/promote-user", json={"firebase_uid": "any-uid"})
    assert res.status_code == 401


# ── 2. Ordinary Admin Rejection (403 Forbidden) ──────────────────────────────

def test_ordinary_admin_cannot_list_admins(client):
    """Ordinary Admin calling Super Admin endpoint receives 403 Forbidden."""
    app.dependency_overrides[get_current_user] = lambda: _ORDINARY_ADMIN
    try:
        res = client.get("/api/v1/admin/roles/admins", headers={"Authorization": "Bearer admin-token"})
        assert res.status_code == 403
        assert "Required role(s): SUPER_ADMIN" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_ordinary_admin_cannot_promote_user(client):
    """Ordinary Admin calling promote endpoint receives 403 Forbidden."""
    app.dependency_overrides[get_current_user] = lambda: _ORDINARY_ADMIN
    try:
        res = client.post(
            "/api/v1/admin/roles/promote-user",
            json={"firebase_uid": _REGULAR_USER["firebase_uid"]},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_ordinary_admin_cannot_revoke_admin(client):
    """Ordinary Admin calling revoke endpoint receives 403 Forbidden."""
    app.dependency_overrides[get_current_user] = lambda: _ORDINARY_ADMIN
    try:
        res = client.delete(
            f"/api/v1/admin/roles/revoke/{_ORDINARY_ADMIN['firebase_uid']}",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_ordinary_admin_cannot_preauthorize_email(client):
    """Ordinary Admin calling pre-authorize endpoint receives 403 Forbidden."""
    app.dependency_overrides[get_current_user] = lambda: _ORDINARY_ADMIN
    try:
        res = client.post(
            "/api/v1/admin/roles/preauthorize",
            json={"email": "newadmin@example.com"},
            headers={"Authorization": "Bearer admin-token"},
        )
        assert res.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ── 3. GET /admin/me ──────────────────────────────────────────────────────────

def test_admin_me_ordinary_admin_success(client):
    """Ordinary admin receives admin profile with is_super_admin=False."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_firebase_token] = lambda: {
        "uid": _ORDINARY_ADMIN["firebase_uid"],
        "email": _ORDINARY_ADMIN["email"],
        "email_verified": True,
        "name": _ORDINARY_ADMIN["display_name"],
    }
    with patch("app.services.admin_roles_service.AdminRolesService.resolve_and_claim_admin", return_value=_ORDINARY_ADMIN):
        try:
            res = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer token"})
            assert res.status_code == 200
            data = res.json()
            assert data["role"] == "ADMIN"
            assert data["is_super_admin"] is False
            assert data["email"] == _ORDINARY_ADMIN["email"]
        finally:
            app.dependency_overrides.clear()


def test_admin_me_super_admin_success(client):
    """Super admin receives admin profile with is_super_admin=True."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_firebase_token] = lambda: {
        "uid": _SUPER_ADMIN["firebase_uid"],
        "email": _SUPER_ADMIN["email"],
        "email_verified": True,
        "name": _SUPER_ADMIN["display_name"],
    }
    with patch("app.services.admin_roles_service.AdminRolesService.resolve_and_claim_admin", return_value=_SUPER_ADMIN):
        try:
            res = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer token"})
            assert res.status_code == 200
            data = res.json()
            assert data["role"] == "SUPER_ADMIN"
            assert data["is_super_admin"] is True
        finally:
            app.dependency_overrides.clear()


def test_admin_me_regular_user_forbidden(client):
    """Regular user hitting /admin/me receives 403 Forbidden."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_firebase_token] = lambda: {
        "uid": _REGULAR_USER["firebase_uid"],
        "email": _REGULAR_USER["email"],
        "email_verified": True,
    }
    with patch("app.services.admin_roles_service.AdminRolesService.resolve_and_claim_admin", return_value=_REGULAR_USER):
        try:
            res = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer token"})
            assert res.status_code == 403
            assert "Access restricted" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()


# ── 4. Super Admin: List Admins ───────────────────────────────────────────────

def test_super_admin_list_admins_success(client):
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([_SUPER_ADMIN, _ORDINARY_ADMIN])

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.get("/api/v1/admin/roles/admins", headers={"Authorization": "Bearer sa-token"})
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["data"][0]["role"] == "SUPER_ADMIN"
        assert data["data"][1]["role"] == "ADMIN"
        assert data["data"][1]["previous_role"] == "CONTRIBUTOR"
    finally:
        app.dependency_overrides.clear()


# ── 5. Method 1: Promote Registered User ──────────────────────────────────────

def test_promote_registered_user_success(client):
    """Super Admin promotes user to Admin; previous_role is preserved."""
    mock_db = MagicMock()
    user_to_promote = {**_CONTRIBUTOR_USER}
    promoted_user = {**_CONTRIBUTOR_USER, "role": "ADMIN", "previous_role": "CONTRIBUTOR"}

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "select" in sql and "from users" in sql:
            return MockResult([user_to_promote])
        if "update users" in sql:
            return MockResult([promoted_user])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.post(
            "/api/v1/admin/roles/promote-user",
            json={"firebase_uid": _CONTRIBUTOR_USER["firebase_uid"]},
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["user"]["role"] == "ADMIN"
        assert data["user"]["previous_role"] == "CONTRIBUTOR"
    finally:
        app.dependency_overrides.clear()


def test_promote_already_admin_fails(client):
    """Attempting to promote an active Admin returns 400 Bad Request."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([_ORDINARY_ADMIN])

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.post(
            "/api/v1/admin/roles/promote-user",
            json={"firebase_uid": _ORDINARY_ADMIN["firebase_uid"]},
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 400
        assert "already an Administrator" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_promote_super_admin_fails(client):
    """Attempting to promote or modify the Super Admin returns 400."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([_SUPER_ADMIN])

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.post(
            "/api/v1/admin/roles/promote-user",
            json={"firebase_uid": _SUPER_ADMIN["firebase_uid"]},
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 400
        assert "Primary Super Admin" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── 6. Revoke Admin Role ──────────────────────────────────────────────────────

def test_revoke_admin_restores_previous_role(client):
    """Revoking Admin role restores previous_role (CONTRIBUTOR) and clears previous_role."""
    mock_db = MagicMock()
    admin_to_revoke = {**_ORDINARY_ADMIN}
    restored_user = {**_ORDINARY_ADMIN, "role": "CONTRIBUTOR", "previous_role": None}

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "select" in sql and "from users" in sql:
            return MockResult([admin_to_revoke])
        if "update users" in sql:
            return MockResult([restored_user])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.delete(
            f"/api/v1/admin/roles/revoke/{_ORDINARY_ADMIN['firebase_uid']}",
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["user"]["role"] == "CONTRIBUTOR"
        assert "restored to CONTRIBUTOR" in data["message"]
    finally:
        app.dependency_overrides.clear()


def test_revoke_self_demotion_fails(client):
    """Super Admin cannot remove their own access."""
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.delete(
            f"/api/v1/admin/roles/revoke/{_SUPER_ADMIN['firebase_uid']}",
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 400
        assert "Cannot remove your own" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


# ── 7. Method 2: Pre-authorize Admin by Email ─────────────────────────────────

def test_preauthorize_email_success(client):
    """Super Admin pre-authorizes email; pending appointment recorded."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "select" in sql and "from users" in sql:
            return MockResult([])  # Not registered yet
        if "select" in sql and "from pending_admin_appointments" in sql:
            return MockResult([])  # No duplicate
        if "insert into pending_admin_appointments" in sql:
            return MockResult([
                {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "email": "neweducator@gmail.com",
                    "normalized_email": "neweducator@gmail.com",
                    "created_by_uid": _SUPER_ADMIN["firebase_uid"],
                    "created_by_email": _SUPER_ADMIN["email"],
                    "status": "pending",
                    "created_at": datetime.now(),
                }
            ])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.post(
            "/api/v1/admin/roles/preauthorize",
            json={"email": "neweducator@gmail.com"},
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["success"] is True
        assert "Successfully pre-authorized" in data["message"]
    finally:
        app.dependency_overrides.clear()


def test_preauthorize_super_admin_email_fails(client):
    """Cannot pre-authorize the Super Admin email."""
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.post(
            "/api/v1/admin/roles/preauthorize",
            json={"email": "hungrylearner786@gmail.com"},
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 400
        assert "Primary Super Admin" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_preauthorize_duplicate_pending_fails(client):
    """Duplicate pre-authorization returns 400 Bad Request."""
    mock_db = MagicMock()

    def _exec(stmt, params=None):
        sql = str(stmt).lower()
        if "from users" in sql:
            return MockResult([])
        if "from pending_admin_appointments" in sql:
            return MockResult([{"id": "exist-id", "email": "dup@gmail.com", "status": "pending"}])
        return MockResult([])

    mock_db.execute.side_effect = _exec
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.post(
            "/api/v1/admin/roles/preauthorize",
            json={"email": "dup@gmail.com"},
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 400
        assert "already pending" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_revoke_pending_appointment_success(client):
    """Super Admin revokes a pending appointment before sign-in."""
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([
        {
            "id": "appt-123",
            "email": "pending@gmail.com",
            "normalized_email": "pending@gmail.com",
            "created_by_uid": _SUPER_ADMIN["firebase_uid"],
            "created_by_email": _SUPER_ADMIN["email"],
            "status": "revoked",
            "created_at": datetime.now(),
        }
    ])

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: _SUPER_ADMIN

    try:
        res = client.delete(
            "/api/v1/admin/roles/pending/appt-123",
            headers={"Authorization": "Bearer sa-token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "Successfully revoked pending appointment" in data["message"]
    finally:
        app.dependency_overrides.clear()

