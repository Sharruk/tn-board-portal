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
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
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
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
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
        if "admin_activity_logs" in sql:
            return MockResult([{"id": "audit-mock-1", "metadata": "{}"}])
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


# ── 8. Stage 3B.1: Envelope Parsing, Audit Atomicity & Security ───────────────

def test_stage_3b1_envelope_parsing_dict_and_string():
    """Verify repository parses both dictionary and JSON string envelopes from Migration 031."""
    from app.repositories.admin_roles_repository import AdminRolesRepository, AppointmentClaimResult

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    envelope_dict = {
        "user": {
            "id": "11111111-1111-1111-1111-111111111111",
            "firebase_uid": "uid-claimant-123",
            "email": "claimant@example.com",
            "display_name": "New Admin",
            "role": "ADMIN",
            "is_active": True,
        },
        "claimed": True,
        "appointment_id": "appt-uuid-999",
        "assigned_role": "ADMIN",
    }

    # Case A: Returned as Python dict (direct JSONB mapping)
    mock_db.execute.return_value = MockResult([[envelope_dict]])
    res_a = repo.claim_pending_appointment_atomic("uid-claimant-123", "claimant@example.com", "New Admin", None)
    assert isinstance(res_a, AppointmentClaimResult)
    assert res_a.claimed is True
    assert res_a.appointment_id == "appt-uuid-999"
    assert res_a.assigned_role == "ADMIN"
    assert res_a.user["id"] == "11111111-1111-1111-1111-111111111111"
    # Invariant: repository MUST NOT commit
    mock_db.commit.assert_not_called()

    # Case B: Returned as JSON string (stringified JSONB)
    import json
    mock_db.execute.return_value = MockResult([[json.dumps(envelope_dict)]])
    res_b = repo.claim_pending_appointment_atomic("uid-claimant-123", "claimant@example.com", "New Admin", None)
    assert res_b.claimed is True
    assert res_b.appointment_id == "appt-uuid-999"
    assert res_b.user["email"] == "claimant@example.com"
    mock_db.commit.assert_not_called()


def test_stage_3b1_legacy_flat_response_handling():
    """Verify repository safely handles legacy Migration 029 flat user responses."""
    from app.repositories.admin_roles_repository import AdminRolesRepository, AppointmentClaimResult

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    legacy_user = {
        "id": "11111111-1111-1111-1111-111111111111",
        "firebase_uid": "uid-legacy-admin",
        "email": "legacy@example.com",
        "display_name": "Legacy Admin",
        "role": "ADMIN",
        "is_active": True,
    }

    mock_db.execute.return_value = MockResult([[legacy_user]])
    res = repo.claim_pending_appointment_atomic("uid-legacy-admin", "legacy@example.com", "Legacy Admin", None)
    assert isinstance(res, AppointmentClaimResult)
    assert res.claimed is False
    assert res.appointment_id is None
    assert res.user["id"] == "11111111-1111-1111-1111-111111111111"
    assert res.user["role"] == "ADMIN"
    mock_db.commit.assert_not_called()


def test_stage_3b1_actual_claim_produces_exactly_one_audit_event():
    """An actual confirmed appointment claim emits APPOINTMENT_CLAIMED inside the same transaction."""
    from app.services.admin_roles_service import AdminRolesService
    from app.repositories.admin_roles_repository import AppointmentClaimResult

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    claim_res = AppointmentClaimResult(
        user={
            "id": "11111111-1111-1111-1111-111111111111",
            "firebase_uid": "uid-new-admin",
            "email": "newadmin@example.com",
            "display_name": "New Admin User",
            "role": "ADMIN",
            "is_active": True,
        },
        claimed=True,
        appointment_id="appt-uuid-555",
        assigned_role="ADMIN",
    )

    with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=claim_res), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "uid-new-admin", "email": "newadmin@example.com", "name": "New Admin User", "email_verified": True}
        user = service.resolve_and_claim_admin(token, ip_address="192.168.1.100")

        assert user["role"] == "ADMIN"
        # Exactly one audit event emitted
        mock_log.assert_called_once_with(
            actor_uid="uid-new-admin",
            actor_email="newadmin@example.com",
            actor_name="New Admin User",
            actor_role="ADMIN",
            action="APPOINTMENT_CLAIMED",
            target_type="admin_appointment",
            target_id="appt-uuid-555",
            target_title="Admin appointment claimed by newadmin@example.com",
            reason="Pre-authorized admin appointment claimed upon login",
            metadata={"assigned_role": "ADMIN", "appointment_id": "appt-uuid-555"},
            ip_address="192.168.1.100",
        )
        # Exactly one commit of the combined transaction
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b1_ordinary_login_produces_no_audit_event():
    """Ordinary subsequent login by an existing admin (claimed=False) produces zero audit events."""
    from app.services.admin_roles_service import AdminRolesService
    from app.repositories.admin_roles_repository import AppointmentClaimResult

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    ordinary_res = AppointmentClaimResult(
        user={
            "id": "11111111-1111-1111-1111-111111111111",
            "firebase_uid": "uid-existing-admin",
            "email": "admin@example.com",
            "display_name": "Existing Admin",
            "role": "ADMIN",
            "is_active": True,
        },
        claimed=False,
        appointment_id=None,
        assigned_role=None,
    )

    with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=ordinary_res), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "uid-existing-admin", "email": "admin@example.com", "name": "Existing Admin", "email_verified": True}
        user = service.resolve_and_claim_admin(token, ip_address="192.168.1.100")

        assert user["role"] == "ADMIN"
        # Zero audit events logged
        mock_log.assert_not_called()
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b1_repeated_login_produces_no_duplicate_audit():
    """Verify claim event on first login, followed by zero audit events on second login."""
    from app.services.admin_roles_service import AdminRolesService
    from app.repositories.admin_roles_repository import AppointmentClaimResult

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    claim_1 = AppointmentClaimResult(
        user={"id": "111", "firebase_uid": "uid-1", "email": "a@b.com", "role": "ADMIN", "is_active": True},
        claimed=True,
        appointment_id="appt-1",
        assigned_role="ADMIN",
    )
    claim_2 = AppointmentClaimResult(
        user={"id": "111", "firebase_uid": "uid-1", "email": "a@b.com", "role": "ADMIN", "is_active": True},
        claimed=False,
        appointment_id=None,
        assigned_role=None,
    )

    token = {"uid": "uid-1", "email": "a@b.com", "name": "User", "email_verified": True}

    with patch.object(service._activity_repo, "log_activity") as mock_log:
        # First login (claim occurred)
        with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=claim_1):
            service.resolve_and_claim_admin(token)
            assert mock_log.call_count == 1

        # Second login (already claimed)
        with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=claim_2):
            service.resolve_and_claim_admin(token)
            # Call count remains 1 (no duplicate audit event!)
            assert mock_log.call_count == 1


def test_stage_3b1_audit_failure_rolls_back_transaction():
    """If audit log insertion fails, the entire transaction is rolled back and no commit occurs."""
    from app.services.admin_roles_service import AdminRolesService
    from app.repositories.admin_roles_repository import AppointmentClaimResult

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    claim_res = AppointmentClaimResult(
        user={"id": "111", "firebase_uid": "uid-1", "email": "a@b.com", "role": "ADMIN", "is_active": True},
        claimed=True,
        appointment_id="appt-1",
        assigned_role="ADMIN",
    )

    with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=claim_res), \
         patch.object(service._activity_repo, "log_activity", side_effect=RuntimeError("Audit DB Error")):

        token = {"uid": "uid-1", "email": "a@b.com", "name": "User", "email_verified": True}
        with pytest.raises(RuntimeError, match="Audit DB Error"):
            service.resolve_and_claim_admin(token)

        # Rollback was executed and commit was NOT executed
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()


def test_stage_3b1_account_conflict_maps_to_409(client):
    """Account conflict raised from repository/RPC cleanly maps to HTTP 409 Conflict."""
    from app.repositories.admin_roles_repository import AccountConflictError

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_firebase_token] = lambda: {
        "uid": "uid-intruder-999",
        "email": "claimed@example.com",
        "email_verified": True,
        "name": "Intruder",
    }

    conflict_err = "Account conflict: Email claimed@example.com is registered under a different UID."
    with patch("app.services.admin_roles_service.AdminRolesService.resolve_and_claim_admin", side_effect=AccountConflictError(conflict_err)):
        try:
            res = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer token"})
            assert res.status_code == 409
            assert "Account conflict" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()


def test_stage_3b1_malformed_rpc_value_error_is_not_converted_to_409():
    """Malformed RPC payload ValueError must NOT be mapped to HTTP 409."""
    from fastapi.testclient import TestClient
    unhandled_client = TestClient(app, raise_server_exceptions=False)

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_firebase_token] = lambda: {
        "uid": "uid-user-1",
        "email": "user@example.com",
        "email_verified": True,
        "name": "User",
    }

    with patch(
        "app.services.admin_roles_service.AdminRolesService.resolve_and_claim_admin",
        side_effect=ValueError("Malformed appointment claim payload structure: {}"),
    ):
        try:
            res = unhandled_client.get("/api/v1/admin/me", headers={"Authorization": "Bearer token"})
            assert res.status_code == 500
            assert res.status_code != 409
        finally:
            app.dependency_overrides.clear()


def test_stage_3b1_unrelated_application_value_error_is_not_converted_to_409():
    """Unrelated application ValueError must NOT be mapped to HTTP 409."""
    from fastapi.testclient import TestClient
    unhandled_client = TestClient(app, raise_server_exceptions=False)

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_firebase_token] = lambda: {
        "uid": "uid-user-2",
        "email": "user2@example.com",
        "email_verified": True,
        "name": "User 2",
    }

    with patch(
        "app.services.admin_roles_service.AdminRolesService.resolve_and_claim_admin",
        side_effect=ValueError("invalid literal for int() with base 10: 'abc'"),
    ):
        try:
            res = unhandled_client.get("/api/v1/admin/me", headers={"Authorization": "Bearer token"})
            assert res.status_code == 500
            assert res.status_code != 409
        finally:
            app.dependency_overrides.clear()


def test_stage_3b1_admin_me_response_schema_preserved(client):
    """GET /api/v1/admin/me returns exact AdminMeResponse schema."""
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
            # Assert all expected fields are present with correct types
            assert set(data.keys()) == {"id", "firebase_uid", "email", "display_name", "photo_url", "role", "is_super_admin"}
            assert data["role"] == "ADMIN"
            assert data["is_super_admin"] is False
        finally:
            app.dependency_overrides.clear()


def test_stage_3b1_disabled_admin_cannot_access(client):
    """Disabled admin account (is_active=False) receives 403 Forbidden on /admin/me."""
    mock_db = MagicMock()
    disabled_admin = {**_ORDINARY_ADMIN, "is_active": False}
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[verify_firebase_token] = lambda: {
        "uid": disabled_admin["firebase_uid"],
        "email": disabled_admin["email"],
        "email_verified": True,
        "name": disabled_admin["display_name"],
    }

    with patch("app.services.admin_roles_service.AdminRolesService.resolve_and_claim_admin", return_value=disabled_admin):
        try:
            res = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer token"})
            assert res.status_code == 403
            assert "Account is disabled" in res.json()["detail"]
        finally:
            app.dependency_overrides.clear()


def test_stage_3b1_super_admin_behavior_preserved(client):
    """Super Admin login continues to return role=SUPER_ADMIN and is_super_admin=True."""
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
            res = client.get("/api/v1/admin/me", headers={"Authorization": "Bearer sa-token"})
            assert res.status_code == 200
            data = res.json()
            assert data["role"] == "SUPER_ADMIN"
            assert data["is_super_admin"] is True
            assert data["email"] == _SUPER_ADMIN["email"]
        finally:
            app.dependency_overrides.clear()


def test_stage_3b1_rpc_uses_savepoint_and_releases_on_success():
    """Verify RPC call executes inside a savepoint (begin_nested) and leaves outer transaction open."""
    from app.repositories.admin_roles_repository import AdminRolesRepository, AppointmentClaimResult

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    envelope = {
        "user": {"id": "111", "firebase_uid": "uid-1", "email": "a@b.com", "role": "ADMIN", "is_active": True},
        "claimed": True,
        "appointment_id": "appt-123",
        "assigned_role": "ADMIN",
    }
    mock_db.execute.return_value = MockResult([[envelope]])

    res = repo.claim_pending_appointment_atomic("uid-1", "a@b.com", "Admin", None)

    # Savepoint was created for the RPC execution
    mock_db.begin_nested.assert_called_once()
    assert isinstance(res, AppointmentClaimResult)
    assert res.claimed is True
    # Outer transaction must NOT be committed or rolled back by repository
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_undefined_column_propagates_without_fallback():
    """Verify that an UndefinedColumn error propagates immediately and does not trigger fallback."""
    from sqlalchemy.exc import ProgrammingError
    from app.repositories.admin_roles_repository import AdminRolesRepository

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    # Simulate PostgreSQL UndefinedColumn (SQLSTATE 42703)
    orig_exc = MagicMock()
    orig_exc.pgcode = "42703"
    db_err = ProgrammingError("SELECT claim_pending_admin_appointment(...)", {}, orig_exc)
    mock_db.execute.side_effect = db_err

    with pytest.raises(ProgrammingError):
        repo.claim_pending_appointment_atomic("uid-1", "test@example.com", "Test", None)

    # Savepoint was created
    mock_db.begin_nested.assert_called_once()
    # Exactly one execution occurred (the RPC call), NO fallback queries!
    assert mock_db.execute.call_count == 1
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_insufficient_privilege_propagates_without_fallback():
    """Verify that InsufficientPrivilege (SQLSTATE 42501) propagates immediately without fallback."""
    from sqlalchemy.exc import ProgrammingError
    from app.repositories.admin_roles_repository import AdminRolesRepository

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    orig_exc = MagicMock()
    orig_exc.pgcode = "42501"
    db_err = ProgrammingError("permission denied for function claim_pending_admin_appointment", {}, orig_exc)
    mock_db.execute.side_effect = db_err

    with pytest.raises(ProgrammingError):
        repo.claim_pending_appointment_atomic("uid-1", "test@example.com", "Test", None)

    mock_db.begin_nested.assert_called_once()
    assert mock_db.execute.call_count == 1
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_operational_connection_error_propagates_without_fallback():
    """Verify that OperationalError (connection drop) propagates immediately without fallback."""
    from sqlalchemy.exc import OperationalError
    from app.repositories.admin_roles_repository import AdminRolesRepository

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    orig_exc = MagicMock()
    orig_exc.pgcode = "08006"
    db_err = OperationalError("connection to server was lost", {}, orig_exc)
    mock_db.execute.side_effect = db_err

    with pytest.raises(OperationalError):
        repo.claim_pending_appointment_atomic("uid-1", "test@example.com", "Test", None)

    mock_db.begin_nested.assert_called_once()
    assert mock_db.execute.call_count == 1
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_undefined_function_rpc_missing_propagates_as_fatal_deployment_error():
    """Verify that a missing RPC function (SQLSTATE 42883) propagates as a fatal deployment error without fallback."""
    from sqlalchemy.exc import ProgrammingError
    from app.repositories.admin_roles_repository import AdminRolesRepository

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    orig_exc = MagicMock()
    orig_exc.pgcode = "42883"
    db_err = ProgrammingError("function claim_pending_admin_appointment does not exist", {}, orig_exc)
    mock_db.execute.side_effect = db_err

    with pytest.raises(ProgrammingError):
        repo.claim_pending_appointment_atomic("uid-1", "test@example.com", "Test", None)

    mock_db.begin_nested.assert_called_once()
    assert mock_db.execute.call_count == 1
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_empty_or_malformed_rpc_payload_propagates_error():
    """Verify that empty RPC result or malformed payload structure raises without fallback."""
    import json
    from app.repositories.admin_roles_repository import AdminRolesRepository

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    # Subcase A: None row returned
    mock_db.execute.return_value = MockResult([])
    with pytest.raises(RuntimeError, match="RPC returned empty result"):
        repo.claim_pending_appointment_atomic("uid-1", "test@example.com", "Test", None)

    # Subcase B: Invalid JSON string
    mock_db.execute.return_value = MockResult([["{invalid-json: missing quotes"]])
    with pytest.raises(json.JSONDecodeError):
        repo.claim_pending_appointment_atomic("uid-1", "test@example.com", "Test", None)

    # Subcase C: Unexpected dictionary structure (not envelope and not legacy flat user)
    mock_db.execute.return_value = MockResult([[{"unexpected_key": "unexpected_val"}]])
    with pytest.raises(ValueError, match="Malformed appointment claim payload structure"):
        repo.claim_pending_appointment_atomic("uid-1", "test@example.com", "Test", None)

    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_rpc_account_conflict_with_diag_pgcode_maps_to_account_conflict_error():
    """Verify that PostgreSQL ACCOUNT_CONFLICT with SQLSTATE P0001 and diag message maps to AccountConflictError."""
    from sqlalchemy.exc import InternalError
    from app.repositories.admin_roles_repository import AccountConflictError, AdminRolesRepository

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    # Simulate PostgreSQL RAISE EXCEPTION 'ACCOUNT_CONFLICT: ...' wrapped in SQLAlchemy InternalError
    mock_orig = MagicMock()
    mock_orig.pgcode = "P0001"
    mock_diag = MagicMock()
    mock_diag.message_primary = "ACCOUNT_CONFLICT: Email conflict@example.com is already registered to another UID (existing_uid=uid-existing, current_uid=uid-conflict)."
    mock_orig.diag = mock_diag
    db_exc = InternalError("SELECT claim_pending_admin_appointment(...)", {}, mock_orig)
    mock_db.execute.side_effect = db_exc

    with pytest.raises(AccountConflictError, match="Account conflict: Email conflict@example.com is registered under a different UID."):
        repo.claim_pending_appointment_atomic("uid-conflict", "conflict@example.com", "Conflict User", None)

    mock_db.begin_nested.assert_called_once()
    assert mock_db.execute.call_count == 1
    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_is_account_conflict_exception_unit_tests():
    """Unit test _is_account_conflict_exception ensuring strict classification and fail-closed safety."""
    from sqlalchemy.exc import DBAPIError
    from app.repositories.admin_roles_repository import AccountConflictError, _is_account_conflict_exception

    # 1. Dedicated AccountConflictError instance -> True
    assert _is_account_conflict_exception(AccountConflictError("Account conflict")) is True

    # 2. Genuine DBAPI error with SQLSTATE P0001 and diag.message_primary starting with ACCOUNT_CONFLICT: -> True
    orig_genuine = MagicMock()
    orig_genuine.pgcode = "P0001"
    orig_genuine.diag.message_primary = "ACCOUNT_CONFLICT: Email registered to another UID."
    exc_genuine = MagicMock(orig=orig_genuine)
    assert _is_account_conflict_exception(exc_genuine) is True

    # 3. Genuine DBAPI error with P0001 without diag, but str(target) starts with ACCOUNT_CONFLICT: -> True
    class FakeDriverP0001(Exception):
        pgcode = "P0001"
        diag = None
    exc_no_diag = MagicMock(orig=FakeDriverP0001("ACCOUNT_CONFLICT: Email registered"))
    assert _is_account_conflict_exception(exc_no_diag) is True

    # 4. Generic P0001 with INVALID_UID diagnostic -> False (must NOT be classified as account conflict)
    orig_invalid_uid = MagicMock()
    orig_invalid_uid.pgcode = "P0001"
    orig_invalid_uid.diag.message_primary = "INVALID_UID: Firebase UID parameter is required and cannot be empty."
    exc_invalid_uid = MagicMock(orig=orig_invalid_uid)
    assert _is_account_conflict_exception(exc_invalid_uid) is False

    # 5. Generic P0001 with INVALID_EMAIL diagnostic -> False (must NOT be classified as account conflict)
    orig_invalid_email = MagicMock()
    orig_invalid_email.pgcode = "P0001"
    orig_invalid_email.diag.message_primary = "INVALID_EMAIL: Email parameter is required and cannot be empty or whitespace-only."
    exc_invalid_email = MagicMock(orig=orig_invalid_email)
    assert _is_account_conflict_exception(exc_invalid_email) is False

    # 6. Database exception containing ACCOUNT_CONFLICT ONLY in SQL parameters -> False (false-positive prevention)
    orig_timeout = MagicMock()
    orig_timeout.pgcode = "57014"  # query_canceled
    orig_timeout.diag.message_primary = "canceling statement due to statement timeout"
    # Construct a SQLAlchemy DBAPIError where SQL params include ACCOUNT_CONFLICT
    db_param_exc = DBAPIError(
        statement="SELECT claim_pending_admin_appointment(:uid, :email, :name, :photo)",
        params={"uid": "u1", "email": "e1", "name": "ACCOUNT_CONFLICT", "photo": None},
        orig=orig_timeout,
    )
    assert _is_account_conflict_exception(db_param_exc) is False

    # 7. Unrelated timeout (pgcode 57014) -> False
    orig_timeout_only = MagicMock()
    orig_timeout_only.pgcode = "57014"
    orig_timeout_only.diag.message_primary = "statement timeout"
    assert _is_account_conflict_exception(MagicMock(orig=orig_timeout_only)) is False

    # 8. Unrelated connection error (pgcode 08006) -> False
    orig_conn = MagicMock()
    orig_conn.pgcode = "08006"
    assert _is_account_conflict_exception(MagicMock(orig=orig_conn)) is False

    # 9. PostgreSQL UndefinedColumn error (pgcode 42703) -> False
    orig_undef_col = MagicMock()
    orig_undef_col.pgcode = "42703"
    orig_undef_col.diag.message_primary = 'column "foo" does not exist'
    assert _is_account_conflict_exception(MagicMock(orig=orig_undef_col)) is False

    # 10. PostgreSQL UndefinedFunction error (pgcode 42883) -> False
    orig_undef_func = MagicMock()
    orig_undef_func.pgcode = "42883"
    orig_undef_func.diag.message_primary = "function claim_pending_admin_appointment does not exist"
    assert _is_account_conflict_exception(MagicMock(orig=orig_undef_func)) is False

    # 11. Plain generic Exception containing text without P0001 -> False (fails closed)
    exc_plain_text = RuntimeError("ACCOUNT_CONFLICT: Email already registered")
    assert _is_account_conflict_exception(exc_plain_text) is False

    # 12. Plain ValueError -> False
    assert _is_account_conflict_exception(ValueError("invalid literal")) is False


def test_stage_3b1_rpc_user_id_validation_envelope_format():
    """Verify strict user ID validation under Migration 031 envelope format."""
    from app.repositories.admin_roles_repository import AdminRolesRepository, AppointmentClaimResult

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    # 1. Valid user ID succeeds
    valid_envelope = {
        "user": {"id": "11111111-1111-1111-1111-111111111111", "email": "valid@example.com", "role": "ADMIN"},
        "claimed": True,
        "appointment_id": "appt-1",
        "assigned_role": "ADMIN",
    }
    mock_db.execute.return_value = MockResult([[valid_envelope]])
    res = repo.claim_pending_appointment_atomic("uid-1", "valid@example.com", "Valid User", None)
    assert isinstance(res, AppointmentClaimResult)
    assert res.user["id"] == "11111111-1111-1111-1111-111111111111"

    # 2. Missing 'id' key in user dictionary is rejected
    missing_id_envelope = {
        "user": {"email": "noid@example.com", "role": "ADMIN"},
        "claimed": True,
        "appointment_id": "appt-1",
    }
    mock_db.execute.return_value = MockResult([[missing_id_envelope]])
    with pytest.raises(ValueError, match="missing 'id'"):
        repo.claim_pending_appointment_atomic("uid-1", "noid@example.com", "No Id", None)

    # 3. Null 'id' value is rejected
    null_id_envelope = {
        "user": {"id": None, "email": "nullid@example.com", "role": "ADMIN"},
        "claimed": True,
        "appointment_id": "appt-1",
    }
    mock_db.execute.return_value = MockResult([[null_id_envelope]])
    with pytest.raises(ValueError, match="null 'id'"):
        repo.claim_pending_appointment_atomic("uid-1", "nullid@example.com", "Null Id", None)

    # 4. Empty string 'id' is rejected
    empty_id_envelope = {
        "user": {"id": "", "email": "emptyid@example.com", "role": "ADMIN"},
        "claimed": True,
        "appointment_id": "appt-1",
    }
    mock_db.execute.return_value = MockResult([[empty_id_envelope]])
    with pytest.raises(ValueError, match="contains invalid 'id'"):
        repo.claim_pending_appointment_atomic("uid-1", "emptyid@example.com", "Empty Id", None)

    # 5. Whitespace-only string 'id' is rejected
    ws_id_envelope = {
        "user": {"id": "   \t  ", "email": "wsid@example.com", "role": "ADMIN"},
        "claimed": True,
        "appointment_id": "appt-1",
    }
    mock_db.execute.return_value = MockResult([[ws_id_envelope]])
    with pytest.raises(ValueError, match="contains invalid 'id'"):
        repo.claim_pending_appointment_atomic("uid-1", "wsid@example.com", "WS Id", None)

    # 6. Literal string 'None' is rejected
    str_none_envelope = {
        "user": {"id": "None", "email": "noneid@example.com", "role": "ADMIN"},
        "claimed": True,
        "appointment_id": "appt-1",
    }
    mock_db.execute.return_value = MockResult([[str_none_envelope]])
    with pytest.raises(ValueError, match="contains invalid 'id'"):
        repo.claim_pending_appointment_atomic("uid-1", "noneid@example.com", "None Id", None)

    # 7. Literal string 'none' is rejected
    str_none_lower = {
        "user": {"id": "none", "email": "noneid2@example.com", "role": "ADMIN"},
        "claimed": True,
        "appointment_id": "appt-1",
    }
    mock_db.execute.return_value = MockResult([[str_none_lower]])
    with pytest.raises(ValueError, match="contains invalid 'id'"):
        repo.claim_pending_appointment_atomic("uid-1", "noneid2@example.com", "None Id 2", None)

    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_rpc_user_id_validation_flat_format():
    """Verify strict user ID validation under Migration 029 legacy flat response format."""
    from app.repositories.admin_roles_repository import AdminRolesRepository, AppointmentClaimResult

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    # 1. Valid flat user ID succeeds
    valid_flat = {"id": "22222222-2222-2222-2222-222222222222", "email": "legacy@example.com", "role": "ADMIN"}
    mock_db.execute.return_value = MockResult([[valid_flat]])
    res = repo.claim_pending_appointment_atomic("uid-2", "legacy@example.com", "Legacy User", None)
    assert isinstance(res, AppointmentClaimResult)
    assert res.user["id"] == "22222222-2222-2222-2222-222222222222"

    # 2. Null flat ID is rejected
    null_flat = {"id": None, "email": "nullflat@example.com", "role": "ADMIN"}
    mock_db.execute.return_value = MockResult([[null_flat]])
    with pytest.raises(ValueError, match="null 'id'"):
        repo.claim_pending_appointment_atomic("uid-2", "nullflat@example.com", "Null Flat", None)

    # 3. Empty string flat ID is rejected
    empty_flat = {"id": "", "email": "emptyflat@example.com", "role": "ADMIN"}
    mock_db.execute.return_value = MockResult([[empty_flat]])
    with pytest.raises(ValueError, match="contains invalid 'id'"):
        repo.claim_pending_appointment_atomic("uid-2", "emptyflat@example.com", "Empty Flat", None)

    # 4. Whitespace string flat ID is rejected
    ws_flat = {"id": "   ", "email": "wsflat@example.com", "role": "ADMIN"}
    mock_db.execute.return_value = MockResult([[ws_flat]])
    with pytest.raises(ValueError, match="contains invalid 'id'"):
        repo.claim_pending_appointment_atomic("uid-2", "wsflat@example.com", "WS Flat", None)

    # 5. Literal string 'None' flat ID is rejected
    str_none_flat = {"id": "None", "email": "noneflat@example.com", "role": "ADMIN"}
    mock_db.execute.return_value = MockResult([[str_none_flat]])
    with pytest.raises(ValueError, match="contains invalid 'id'"):
        repo.claim_pending_appointment_atomic("uid-2", "noneflat@example.com", "None Flat", None)


def test_stage_3b1_malformed_rpc_id_does_not_produce_audit_event():
    """Verify that a malformed RPC user ID causes outer transaction rollback and emits zero audit events."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    # Repository raises ValueError due to invalid user ID
    with patch.object(service._repo, "claim_pending_appointment_atomic", side_effect=ValueError("RPC claim response user record missing 'id'")), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "uid-err", "email": "err@example.com", "email_verified": True}
        with pytest.raises(ValueError, match="missing 'id'"):
            service.resolve_and_claim_admin(token)

        # Audit event was NEVER called
        mock_log.assert_not_called()
        # Outer transaction was rolled back
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()



def test_stage_3b1_rpc_claimed_strict_boolean_validation():
    """Verify strict type(v) is bool validation for the 'claimed' field in Migration 031 envelope."""
    from app.repositories.admin_roles_repository import AdminRolesRepository, AppointmentClaimResult

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    valid_user = {"id": "11111111-1111-1111-1111-111111111111", "email": "bool@example.com", "role": "ADMIN"}

    # 1. Python True is accepted
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": True, "appointment_id": "appt-1"}]])
    res_true = repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)
    assert res_true.claimed is True

    # 2. Python False is accepted
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": False, "appointment_id": None}]])
    res_false = repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)
    assert res_false.claimed is False

    # 3. String "true" is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": "true", "appointment_id": "appt-1"}]])
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    # 4. String "false" is rejected (must NOT be coerced to True)
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": "false", "appointment_id": "appt-1"}]])
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    # 5. Integer 1 is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": 1, "appointment_id": "appt-1"}]])
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    # 6. Integer 0 is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": 0, "appointment_id": None}]])
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    # 7. None / null is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": None, "appointment_id": None}]])
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    # 8. Missing 'claimed' key is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "appointment_id": None}]])
    with pytest.raises(ValueError, match="missing required 'claimed' field"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    # 9. List [] is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": [], "appointment_id": None}]])
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    # 10. Dict {} is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": {}, "appointment_id": None}]])
    with pytest.raises(ValueError, match="must be an explicit boolean"):
        repo.claim_pending_appointment_atomic("uid-1", "bool@example.com", "User", None)

    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_not_called()


def test_stage_3b1_rpc_appointment_id_consistency_validation():
    """Verify consistency between 'claimed' boolean and 'appointment_id' in Migration 031 envelope."""
    from app.repositories.admin_roles_repository import AdminRolesRepository, AppointmentClaimResult

    mock_db = MagicMock()
    repo = AdminRolesRepository(mock_db)

    valid_user = {"id": "11111111-1111-1111-1111-111111111111", "email": "appt@example.com", "role": "ADMIN"}

    # 1. claimed=True with valid ID is accepted
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": True, "appointment_id": "appt-123"}]])
    res = repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)
    assert res.claimed is True
    assert res.appointment_id == "appt-123"

    # 2. claimed=True with null appointment_id is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": True, "appointment_id": None}]])
    with pytest.raises(ValueError, match="claimed=True requires valid non-null appointment_id"):
        repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)

    # 3. claimed=True with missing appointment_id key is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": True}]])
    with pytest.raises(ValueError, match="claimed=True requires valid non-null appointment_id"):
        repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)

    # 4. claimed=True with empty string appointment_id is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": True, "appointment_id": ""}]])
    with pytest.raises(ValueError, match="claimed=True requires non-empty appointment_id"):
        repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)

    # 5. claimed=True with whitespace-only appointment_id is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": True, "appointment_id": "   \t  "}]])
    with pytest.raises(ValueError, match="claimed=True requires non-empty appointment_id"):
        repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)

    # 5b. claimed=True with non-string types (integer, boolean, list, dict) is strictly rejected
    for invalid_appt_id in [123, True, False, ["appt-1"], {"id": "appt-1"}]:
        mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": True, "appointment_id": invalid_appt_id}]])
        with pytest.raises(ValueError, match="claimed=True requires appointment_id of type str"):
            repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)

    # 6. claimed=False with null appointment_id is accepted
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": False, "appointment_id": None}]])
    res_f1 = repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)
    assert res_f1.claimed is False
    assert res_f1.appointment_id is None

    # 7. claimed=False with missing appointment_id key is accepted
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": False}]])
    res_f2 = repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)
    assert res_f2.claimed is False
    assert res_f2.appointment_id is None

    # 8. claimed=False with populated appointment_id is rejected
    mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": False, "appointment_id": "appt-unexpected"}]])
    with pytest.raises(ValueError, match="claimed=False cannot have populated appointment_id"):
        repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)

    # 8b. claimed=False with non-null non-empty non-string types is rejected
    for invalid_false_appt in [123, True, ["unexpected"]]:
        mock_db.execute.return_value = MockResult([[{"user": valid_user, "claimed": False, "appointment_id": invalid_false_appt}]])
        with pytest.raises(ValueError, match="claimed=False cannot have populated appointment_id"):
            repo.claim_pending_appointment_atomic("uid-1", "appt@example.com", "User", None)


def test_stage_3b1_service_defense_claimed_true_requires_appointment_id():
    """Verify service-level defense: claimed=True without valid appointment_id raises and rolls back."""
    from app.repositories.admin_roles_repository import AppointmentClaimResult
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    # Case A: appointment_id is None
    bad_result_none = AppointmentClaimResult(
        user={"id": "111", "firebase_uid": "u1", "email": "e@test.com", "role": "ADMIN"},
        claimed=True,
        appointment_id=None,
    )
    with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=bad_result_none), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "u1", "email": "e@test.com", "email_verified": True}
        with pytest.raises(ValueError, match="claimed=True.*but appointment_id is missing or invalid"):
            service.resolve_and_claim_admin(token)

        mock_log.assert_not_called()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

    # Case B: appointment_id is empty string
    mock_db.reset_mock()
    bad_result_empty = AppointmentClaimResult(
        user={"id": "111", "firebase_uid": "u1", "email": "e@test.com", "role": "ADMIN"},
        claimed=True,
        appointment_id="",
    )
    with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=bad_result_empty), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "u1", "email": "e@test.com", "email_verified": True}
        with pytest.raises(ValueError, match="claimed=True.*but appointment_id is missing or invalid"):
            service.resolve_and_claim_admin(token)

        mock_log.assert_not_called()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

    # Case C: appointment_id is whitespace
    mock_db.reset_mock()
    bad_result_ws = AppointmentClaimResult(
        user={"id": "111", "firebase_uid": "u1", "email": "e@test.com", "role": "ADMIN"},
        claimed=True,
        appointment_id="   ",
    )
    with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=bad_result_ws), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "u1", "email": "e@test.com", "email_verified": True}
        with pytest.raises(ValueError, match="claimed=True.*but appointment_id is missing or invalid"):
            service.resolve_and_claim_admin(token)

        mock_log.assert_not_called()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()


def test_stage_3b1_service_defense_claimed_false_commits_without_audit():
    """Verify ordinary login with claimed=False commits user record without audit logging."""
    from app.repositories.admin_roles_repository import AppointmentClaimResult
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    claim_result = AppointmentClaimResult(
        user={"id": "111", "firebase_uid": "u1", "email": "admin@test.com", "role": "ADMIN"},
        claimed=False,
        appointment_id=None,
    )
    with patch.object(service._repo, "claim_pending_appointment_atomic", return_value=claim_result), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "u1", "email": "admin@test.com", "email_verified": True}
        user = service.resolve_and_claim_admin(token)

        assert user["role"] == "ADMIN"
        mock_log.assert_not_called()
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b1_malformed_claimed_creates_zero_audit_events_and_rolls_back():
    """Verify that a malformed RPC claimed value rolls back the outer transaction and emits zero audit events."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    # Simulate repository raising ValueError due to malformed claimed field
    with patch.object(service._repo, "claim_pending_appointment_atomic", side_effect=ValueError("RPC claim response 'claimed' field must be an explicit boolean")), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        token = {"uid": "u-bad", "email": "bad@test.com", "email_verified": True}
        with pytest.raises(ValueError, match="must be an explicit boolean"):
            service.resolve_and_claim_admin(token)

        mock_log.assert_not_called()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()

# ── 9. Stage 3B.2: Governance Audit Integration Tests ─────────────────────────

def test_stage_3b2_preauthorize_new_email_audit_and_commit():
    """Verify preauthorizing an unregistered email logs ADMIN_APPOINTMENT_CREATED and commits."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    with patch.object(service._repo, "get_user_by_email", return_value=None), \
         patch.object(service._repo, "get_pending_appointment_by_email", return_value=None), \
         patch.object(service._repo, "create_pending_appointment", return_value={"id": "appt-new-1", "email": "new@test.com"}), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        res = service.preauthorize_email("new@test.com", _SUPER_ADMIN, ip_address="10.0.0.1")
        assert res.success is True

        mock_log.assert_called_once()
        kwargs = mock_log.call_args[1]
        assert kwargs["action"] == "ADMIN_APPOINTMENT_CREATED"
        assert kwargs["target_type"] == "admin_appointment"
        assert kwargs["target_id"] == "appt-new-1"
        assert kwargs["actor_uid"] == _SUPER_ADMIN["firebase_uid"]
        assert kwargs["ip_address"] == "10.0.0.1"
        assert kwargs["metadata"]["email"] == "new@test.com"

        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b2_preauthorize_existing_user_promoted_audit_and_commit():
    """Verify preauthorizing an existing registered user directly upgrades them, logs ADMIN_ROLE_PROMOTED, and commits."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    existing_user = {"id": "u-exist-1", "firebase_uid": "uid-exist", "email": "exist@test.com", "role": "USER", "display_name": "Existing"}
    promoted_record = {**existing_user, "role": "ADMIN", "previous_role": "USER", "is_active": True, "created_at": None, "last_active_at": None, "photo_url": None}

    with patch.object(service._repo, "get_user_by_email", return_value=existing_user), \
         patch.object(service._repo, "get_pending_appointment_by_email", return_value=None), \
         patch.object(service._repo, "promote_user_to_admin", return_value=promoted_record), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        res = service.preauthorize_email("exist@test.com", _SUPER_ADMIN, ip_address="10.0.0.2")
        assert res.success is True
        assert res.user.role == "ADMIN"

        mock_log.assert_called_once()
        kwargs = mock_log.call_args[1]
        assert kwargs["action"] == "ADMIN_ROLE_PROMOTED"
        assert kwargs["target_type"] == "user"
        assert kwargs["target_id"] == "uid-exist"
        assert kwargs["actor_uid"] == _SUPER_ADMIN["firebase_uid"]
        assert kwargs["ip_address"] == "10.0.0.2"

        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b2_revoke_pending_appointment_audit_and_commit():
    """Verify revoking a pending appointment logs ADMIN_APPOINTMENT_REVOKED and commits."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    with patch.object(service._repo, "revoke_pending_appointment", return_value={"id": "appt-rev-1", "email": "rev@test.com", "normalized_email": "rev@test.com"}), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        res = service.revoke_pending_appointment("appt-rev-1", current_user=_SUPER_ADMIN, ip_address="10.0.0.3")
        assert res.success is True

        mock_log.assert_called_once()
        kwargs = mock_log.call_args[1]
        assert kwargs["action"] == "ADMIN_APPOINTMENT_REVOKED"
        assert kwargs["target_type"] == "admin_appointment"
        assert kwargs["target_id"] == "appt-rev-1"
        assert kwargs["actor_uid"] == _SUPER_ADMIN["firebase_uid"]
        assert kwargs["ip_address"] == "10.0.0.3"

        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b2_promote_registered_user_audit_and_commit():
    """Verify promoting a registered user logs ADMIN_ROLE_PROMOTED and commits."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    target_user = {"id": "u-prom-1", "firebase_uid": "uid-prom", "email": "prom@test.com", "role": "CONTRIBUTOR", "display_name": "Prom"}
    promoted_record = {**target_user, "role": "ADMIN", "previous_role": "CONTRIBUTOR", "is_active": True, "created_at": None, "last_active_at": None, "photo_url": None}

    with patch.object(service._repo, "get_user_by_firebase_uid", return_value=target_user), \
         patch.object(service._repo, "promote_user_to_admin", return_value=promoted_record), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        res = service.promote_registered_user("uid-prom", _SUPER_ADMIN, ip_address="10.0.0.4")
        assert res.success is True
        assert res.user.role == "ADMIN"

        mock_log.assert_called_once()
        kwargs = mock_log.call_args[1]
        assert kwargs["action"] == "ADMIN_ROLE_PROMOTED"
        assert kwargs["target_type"] == "user"
        assert kwargs["target_id"] == "uid-prom"
        assert kwargs["actor_uid"] == _SUPER_ADMIN["firebase_uid"]
        assert kwargs["metadata"]["previous_role"] == "CONTRIBUTOR"

        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b2_revoke_admin_role_audit_and_commit():
    """Verify revoking an Admin logs ADMIN_ROLE_REVOKED and commits."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    target_admin = {"id": "u-rev-1", "firebase_uid": "uid-rev", "email": "revadmin@test.com", "role": "ADMIN", "display_name": "RevAdmin"}
    revoked_record = {**target_admin, "role": "CONTRIBUTOR", "previous_role": None, "is_active": True, "created_at": None, "last_active_at": None, "photo_url": None}

    with patch.object(service._repo, "get_user_by_firebase_uid", return_value=target_admin), \
         patch.object(service._repo, "revoke_admin_role", return_value=revoked_record), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        res = service.revoke_admin_role("uid-rev", _SUPER_ADMIN, ip_address="10.0.0.5")
        assert res.success is True
        assert res.user.role == "CONTRIBUTOR"

        mock_log.assert_called_once()
        kwargs = mock_log.call_args[1]
        assert kwargs["action"] == "ADMIN_ROLE_REVOKED"
        assert kwargs["target_type"] == "user"
        assert kwargs["target_id"] == "uid-rev"
        assert kwargs["actor_uid"] == _SUPER_ADMIN["firebase_uid"]
        assert kwargs["metadata"]["restored_role"] == "CONTRIBUTOR"

        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()


def test_stage_3b2_governance_audit_failure_rolls_back_mutation():
    """Verify that an audit log failure rolls back each governance mutation completely."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    target_user = {"id": "u-fail-1", "firebase_uid": "uid-fail", "email": "fail@test.com", "role": "CONTRIBUTOR", "display_name": "Fail"}
    promoted_record = {**target_user, "role": "ADMIN", "previous_role": "CONTRIBUTOR", "is_active": True, "created_at": None, "last_active_at": None, "photo_url": None}

    with patch.object(service._repo, "get_user_by_firebase_uid", return_value=target_user), \
         patch.object(service._repo, "promote_user_to_admin", return_value=promoted_record), \
         patch.object(service._activity_repo, "log_activity", side_effect=RuntimeError("Audit write failure")):

        with pytest.raises(RuntimeError, match="Audit write failure"):
            service.promote_registered_user("uid-fail", _SUPER_ADMIN)

        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()


def test_stage_3b2_mutation_failure_produces_zero_audit_events():
    """Verify that if repository mutation fails or raises, zero audit events are emitted."""
    from app.services.admin_roles_service import AdminRolesService

    mock_db = MagicMock()
    service = AdminRolesService(mock_db)

    with patch.object(service._repo, "get_user_by_email", return_value=None), \
         patch.object(service._repo, "get_pending_appointment_by_email", return_value=None), \
         patch.object(service._repo, "create_pending_appointment", side_effect=RuntimeError("Database write error")), \
         patch.object(service._activity_repo, "log_activity") as mock_log:

        with pytest.raises(RuntimeError, match="Database write error"):
            service.preauthorize_email("fail@test.com", _SUPER_ADMIN)

        mock_log.assert_not_called()
        mock_db.rollback.assert_called_once()
        mock_db.commit.assert_not_called()
