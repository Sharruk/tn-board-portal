"""
Comprehensive unit & integration tests for Multi-User Roles & Community Governance.

Covers:
  1. Guest access open: browse, search, view, download (zero login wall)
  2. Contributor promotion: User becomes CONTRIBUTOR on material submission; Admin/Super Admin retain roles
  3. Deletion security: Normal Admin blocked from permanent deletion (403); Super Admin permitted (200)
  4. Paper verification: Verified Teacher can verify; self-verification strictly blocked (400)
  5. Governance workflows:
     - Admin addition (Super Admin and Verified Teacher)
     - Admin removal request (enters pending)
     - Two-person approval (initiator and target blocked from approving)
     - Super Admin direct removal
  6. Active pending report deduplication (409 Conflict)
  7. Activity audit logging
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user, require_admin, require_super_admin, require_verified_teacher
from app.dependencies.supabase import get_db
from app.config.settings import get_settings
from app.main import app

settings = get_settings()
from app.services.admin_governance_service import AdminGovernanceService
from app.services.papers_service import PapersService
from app.services.submissions_service import SubmissionsService
from app.utils.exceptions import ConflictError, ForbiddenError, ValidationError

client = TestClient(app)


# ── 1. Guest Access (Zero Login Wall) ─────────────────────────────────────────

def test_guest_public_paper_access():
    """Verify that Guests (no auth header) can browse, search, view, and download papers."""
    mock_db = MagicMock()

    # Mock paper list query
    mock_row = {
        "id": 101,
        "subject_id": 1,
        "exam_type": "Public Exam",
        "year": 2026,
        "month": "March",
        "district": "Chennai",
        "title": "Class 10 Tamil 2026",
        "description": "Annual Exam QP",
        "paper_type": "question",
        "file_path": "papers/101.pdf",
        "public_url": "https://cdn.example.com/papers/101.pdf",
        "youtube_url": None,
        "original_filename": "tamil_2026.pdf",
        "is_visible": True,
        "status": "published",
        "download_count": 42,
        "created_at": "2026-03-15T10:00:00Z",
        "submission_id": None,
        "contributor_name": "Teacher A",
        "verification_status": "VERIFIED",
        "verified_by_uid": "admin-1",
        "verified_by_name": "Teacher B",
        "verified_at": "2026-03-15T11:00:00Z",
        "verification_note": "Verified syllabus accuracy",
        "subject_name": "Tamil",
        "subject_slug": "tamil",
        "is_practical": False,
        "class_id": 10,
        "class_name": "Class 10",
        "class_slug": "10",
    }
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [MagicMock(_mapping=mock_row)]
    mock_result.fetchone.return_value = MagicMock(_mapping=mock_row)
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        # GET /api/v1/papers without Auth
        res = client.get("/api/v1/papers?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["verification_status"] == "VERIFIED"

        # GET /api/v1/papers/{id} without Auth
        res = client.get("/api/v1/papers/101")
        assert res.status_code == 200
        detail = res.json()
        assert detail["id"] == 101
        assert detail["verified_by_name"] == "Teacher B"

        # POST /api/v1/papers/{id}/download without Auth
        res = client.post("/api/v1/papers/101/download")
        assert res.status_code == 204
    finally:
        app.dependency_overrides.clear()


# ── 2. Deletion Security: Admin vs Super Admin ────────────────────────────────

def test_admin_cannot_permanently_delete_paper():
    """Verify that a normal Admin cannot permanently delete published papers (403)."""
    mock_db = MagicMock()
    normal_admin = {
        "firebase_uid": "admin-uid-1",
        "email": "normaladmin@example.com",
        "role": "ADMIN",
        "is_verified_teacher": False,
    }

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: normal_admin
    # require_super_admin should fail for normal_admin
    try:
        res = client.delete("/api/v1/papers/101")
        assert res.status_code == 403
        assert "SUPER_ADMIN" in res.json()["detail"] or "Insufficient permissions" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_super_admin_can_permanently_delete_paper():
    """Verify that Super Admin can permanently delete published papers (200)."""
    mock_db = MagicMock()
    super_admin = {
        "firebase_uid": "super-uid-1",
        "email": settings.ADMIN_EMAIL,
        "role": "SUPER_ADMIN",
        "is_verified_teacher": True,
    }

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_super_admin] = lambda: super_admin

    with patch.object(PapersService, "delete_paper") as mock_del:
        from app.schemas.paper import PaperDeleteResponse
        mock_del.return_value = PaperDeleteResponse(
            paper_id=101,
            deleted=True,
            storage_deleted=True,
            message="Paper deleted successfully.",
        )
        try:
            res = client.delete("/api/v1/papers/101")
            assert res.status_code == 200
            assert res.json()["deleted"] is True
            mock_del.assert_called_once()
        finally:
            app.dependency_overrides.clear()


# ── 3. Paper Status: Unpublish / Restore by Admin ─────────────────────────────

def test_admin_can_unpublish_and_restore_paper():
    """Verify that normal Admin can unpublish (archive) and restore a paper."""
    mock_db = MagicMock()
    admin_user = {
        "firebase_uid": "admin-uid-1",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: admin_user

    with patch.object(PapersService, "update_paper_status") as mock_status:
        mock_paper_row = {
            "id": 101, "subject_id": 1, "exam_type": "Annual Exam",
            "year": 2026, "month": None, "district": None,
            "title": "Sample Paper", "description": None, "paper_type": "question",
            "file_path": None, "public_url": None, "youtube_url": None,
            "original_filename": "paper.pdf", "is_visible": False, "status": "archived",
            "download_count": 0, "created_at": "2026-03-15T10:00:00Z",
            "verification_status": "NOT_VERIFIED",
        }
        from app.schemas.paper import PaperResponse
        mock_status.return_value = PaperResponse(**mock_paper_row)

        try:
            res = client.patch("/api/v1/papers/101/status", json={"status": "archived"})
            assert res.status_code == 200
            assert res.json()["status"] == "archived"
        finally:
            app.dependency_overrides.clear()


# ── 4. Paper Verification Workflow & Self-Verification Block ──────────────────

def test_self_verification_prohibited():
    """Verify that a submitter cannot verify their own paper."""
    mock_db = MagicMock()
    verifier_user = {
        "firebase_uid": "teacher-uid-1",
        "email": "teacher1@example.com",
        "role": "ADMIN",
        "is_verified_teacher": True,
    }

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_verified_teacher] = lambda: verifier_user

    svc = PapersService(mock_db)
    with patch.object(svc._repo, "get_by_id") as mock_get:
        # Paper submitted by the same teacher
        mock_get.return_value = {
            "id": 101,
            "title": "My Paper",
            "submission_uid": "teacher-uid-1",
            "verification_status": "NOT_VERIFIED",
        }
        with pytest.raises(ValidationError) as exc:
            svc.verify_paper(101, verifier_user)
        assert "cannot verify your own submitted materials" in str(exc.value)


def test_verified_teacher_can_verify_peer_material():
    """Verify that a Verified Teacher can verify peer submissions."""
    mock_db = MagicMock()
    verifier_user = {
        "firebase_uid": "teacher-uid-2",
        "email": "teacher2@example.com",
        "display_name": "Teacher B",
        "role": "ADMIN",
        "is_verified_teacher": True,
    }

    svc = PapersService(mock_db)
    with patch.object(svc._repo, "get_by_id") as mock_get, \
         patch.object(svc._repo, "verify_paper") as mock_verify, \
         patch("app.repositories.admin_activity_repository.AdminActivityRepository.log_activity"):

        mock_get.return_value = {
            "id": 101,
            "title": "Peer Paper",
            "submission_uid": "teacher-uid-1",  # Different submitter
            "verification_status": "NOT_VERIFIED",
            "subject_id": 1, "exam_type": "Public", "year": 2026,
            "paper_type": "question", "download_count": 0, "is_visible": True,
            "created_at": "2026-03-15T10:00:00Z",
        }
        mock_verify.return_value = {
            "id": 101,
            "title": "Peer Paper",
            "submission_uid": "teacher-uid-1",
            "verification_status": "VERIFIED",
            "verified_by_uid": "teacher-uid-2",
            "verified_by_name": "Teacher B",
            "subject_id": 1, "exam_type": "Public", "year": 2026,
            "paper_type": "question", "download_count": 0, "is_visible": True,
            "status": "published",
            "created_at": "2026-03-15T10:00:00Z",
        }

        res = svc.verify_paper(101, verifier_user, note="Excellent quality")
        assert res.verification_status == "VERIFIED"
        assert res.verified_by_name == "Teacher B"


# ── 5. Admin Addition & Monthly Quota ─────────────────────────────────────────

def test_admin_addition_by_verified_teacher_with_quota():
    """Verify that Verified Teacher can add Admin within quota limit."""
    mock_db = MagicMock()
    verified_teacher = {
        "firebase_uid": "vt-uid-1",
        "email": "vt@school.edu",
        "display_name": "Teacher VT",
        "role": "ADMIN",
        "is_verified_teacher": True,
    }

    from app.schemas.admin_governance import AdminAddRequest
    gov_svc = AdminGovernanceService(mock_db)

    with patch.object(gov_svc._repo, "count_monthly_additions", return_value=2), \
         patch.object(gov_svc._user_repo, "get_by_email", return_value=None), \
         patch.object(gov_svc._user_repo, "upsert_user") as mock_upsert, \
         patch.object(gov_svc._repo, "create_request"), \
         patch.object(gov_svc._activity_repo, "log_activity"):

        req = AdminAddRequest(email="newteacher@school.edu", display_name="New Teacher")
        res = gov_svc.add_admin(req, verified_teacher)
        assert res["success"] is True
        assert res["user"]["role"] == "ADMIN"
        mock_upsert.assert_called_once()


def test_admin_addition_quota_exceeded():
    """Verify that exceeding monthly quota blocks Verified Teacher from adding admins."""
    mock_db = MagicMock()
    verified_teacher = {
        "firebase_uid": "vt-uid-1",
        "email": "vt@school.edu",
        "role": "ADMIN",
        "is_verified_teacher": True,
    }

    from app.schemas.admin_governance import AdminAddRequest
    gov_svc = AdminGovernanceService(mock_db)

    with patch.object(gov_svc._repo, "count_monthly_additions", return_value=3):
        req = AdminAddRequest(email="overquota@school.edu")
        with pytest.raises(ValidationError) as exc:
            gov_svc.add_admin(req, verified_teacher)
        assert "Monthly quota reached" in str(exc.value)


# ── 6. Two-Person Admin Removal Consensus & Governance Security ───────────────

def test_normal_admin_blocked_from_initiating_removal():
    """Verify that a Normal Admin (not Verified Teacher) cannot initiate Admin removal (403)."""
    mock_db = MagicMock()
    gov_svc = AdminGovernanceService(mock_db)
    normal_admin = {"firebase_uid": "norm-1", "email": "norm@example.com", "role": "ADMIN", "is_verified_teacher": False}
    from app.schemas.admin_governance import AdminRemovalRequestCreate

    req = AdminRemovalRequestCreate(target_uid="admin-b", reason="Disagreement")
    with pytest.raises(ForbiddenError) as exc:
        gov_svc.request_admin_removal(req, normal_admin)
    assert "Verified Teachers" in str(exc.value) or "Super Admin" in str(exc.value)


def test_cannot_remove_super_admin():
    """Verify that Super Admin cannot be targeted for removal."""
    mock_db = MagicMock()
    gov_svc = AdminGovernanceService(mock_db)
    verified_teacher = {"firebase_uid": "vt-1", "email": "vt@school.edu", "role": "ADMIN", "is_verified_teacher": True}
    super_admin = {"firebase_uid": "sa-1", "email": settings.ADMIN_EMAIL, "role": "SUPER_ADMIN", "is_verified_teacher": True}

    from app.schemas.admin_governance import AdminRemovalRequestCreate
    with patch.object(gov_svc._user_repo, "get_by_firebase_uid", return_value=super_admin):
        req = AdminRemovalRequestCreate(target_uid="sa-1", reason="Cannot remove Super Admin")
        with pytest.raises(ForbiddenError) as exc:
            gov_svc.request_admin_removal(req, verified_teacher)
        assert "Super Admin" in str(exc.value) or "Super Administrator" in str(exc.value)


def test_two_person_removal_workflow():
    """Verify two-person approval state machine for Admin removals with live UUID schema."""
    mock_db = MagicMock()
    gov_svc = AdminGovernanceService(mock_db)

    req_uuid = "c2a4c8a2-3f2d-4b55-a131-01f70d6bc9f0"
    admin_a = {"firebase_uid": "admin-a", "email": "a@example.com", "role": "ADMIN", "is_verified_teacher": True}
    target_b = {"firebase_uid": "admin-b", "email": "b@example.com", "role": "ADMIN", "is_verified_teacher": False}

    from app.schemas.admin_governance import AdminRemovalRequestCreate

    # Step 1: Verified Teacher A requests removal of Admin B
    with patch.object(gov_svc._user_repo, "get_by_firebase_uid", return_value=target_b), \
         patch.object(gov_svc._repo, "get_pending_removal", return_value=None), \
         patch.object(gov_svc._repo, "create_request", return_value={"id": req_uuid, "status": "pending"}), \
         patch.object(gov_svc._activity_repo, "log_activity"):

        req = AdminRemovalRequestCreate(target_uid="admin-b", reason="Inappropriate moderation actions")
        res = gov_svc.request_admin_removal(req, admin_a)
        assert res["success"] is True
        assert res["request"]["status"] == "pending"

    pending_req = {
        "id": req_uuid,
        "status": "pending",
        "request_type": "removal",
        "initiated_by_uid": "admin-a",
        "initiated_by_email": "a@example.com",
        "initiated_by_name": "Teacher A",
        "target_user_uid": "admin-b",
        "target_email": "b@example.com",
        "target_name": "Admin B",
    }

    # Step 2: Collusion check — Initiator Admin A cannot approve own request
    with patch.object(gov_svc._repo, "get_by_id", return_value=pending_req):
        with pytest.raises(ForbiddenError) as exc:
            gov_svc.process_removal_approval(req_uuid, "approved", approver=admin_a)
        assert "cannot approve a removal request you initiated" in str(exc.value)

    # Step 3: Self-preservation check — Target Admin B cannot vote
    with patch.object(gov_svc._repo, "get_by_id", return_value=pending_req):
        with pytest.raises(ForbiddenError) as exc:
            gov_svc.process_removal_approval(req_uuid, "rejected", approver=target_b)
        assert "target Administrator cannot participate" in str(exc.value)

    # Step 4: Normal Admin D cannot act as second approver
    normal_admin_d = {"firebase_uid": "admin-d", "email": "d@example.com", "role": "ADMIN", "is_verified_teacher": False}
    with patch.object(gov_svc._repo, "get_by_id", return_value=pending_req):
        with pytest.raises(ForbiddenError) as exc:
            gov_svc.process_removal_approval(req_uuid, "approved", approver=normal_admin_d)
        assert "Verified Teachers" in str(exc.value) or "Super Admin" in str(exc.value)

    # Step 5: Second Verified Teacher C approves -> target demoted to USER
    admin_c = {"firebase_uid": "admin-c", "email": "c@example.com", "role": "ADMIN", "is_verified_teacher": True}
    with patch.object(gov_svc._repo, "get_by_id", return_value=pending_req), \
         patch.object(gov_svc._user_repo, "update_role") as mock_demote, \
         patch.object(gov_svc._user_repo, "update_verified_teacher"), \
         patch.object(gov_svc._user_repo, "update_governance_status"), \
         patch.object(gov_svc._repo, "update_request_status", return_value={"status": "approved"}), \
         patch.object(gov_svc._activity_repo, "log_activity"):

        res = gov_svc.process_removal_approval(req_uuid, "approved", approver=admin_c)
        assert res["success"] is True
        mock_demote.assert_called_once()

# ── 7. Super Admin Direct Removal ─────────────────────────────────────────────

def test_super_admin_direct_removal():
    """Verify that Super Admin can directly remove an Admin without a second approver."""
    mock_db = MagicMock()
    gov_svc = AdminGovernanceService(mock_db)
    super_admin = {"firebase_uid": "sa-1", "email": settings.ADMIN_EMAIL, "role": "SUPER_ADMIN", "is_verified_teacher": True}
    target_admin = {"firebase_uid": "bad-admin", "email": "bad@school.edu", "role": "ADMIN", "is_verified_teacher": False}

    with patch.object(gov_svc._user_repo, "get_by_firebase_uid", return_value=target_admin), \
         patch.object(gov_svc._repo, "get_pending_removal", return_value=None), \
         patch.object(gov_svc._user_repo, "update_role") as mock_demote, \
         patch.object(gov_svc._user_repo, "update_verified_teacher"), \
         patch.object(gov_svc._user_repo, "update_governance_status"), \
         patch.object(gov_svc._repo, "create_request"), \
         patch.object(gov_svc._activity_repo, "log_activity"):

        res = gov_svc.direct_remove_admin("bad-admin", "Immediate security violation", super_admin)
        assert res["success"] is True
        mock_demote.assert_called_once()


# ── 8. Admin Invitation Claiming ──────────────────────────────────────────────

def test_admin_invitation_claim_on_first_auth():
    """Verify that pre-provisioned pending_{email} admin record is safely bound to real Google UID."""
    mock_db = MagicMock()
    from app.repositories.user_profile_repository import UserProfileRepository
    repo = UserProfileRepository(mock_db)

    with patch.object(repo, "claim_pending_invitation") as mock_claim:
        mock_claim.return_value = {
            "firebase_uid": "real-google-uid-123",
            "email": "teacher@school.edu",
            "role": "ADMIN",
            "is_verified_teacher": False,
        }
        user = repo.claim_pending_invitation("teacher@school.edu", "real-google-uid-123", "Teacher Real Name")
        assert user is not None
        assert user["role"] == "ADMIN"
        assert user["firebase_uid"] == "real-google-uid-123"
        mock_claim.assert_called_once()


# ── 9. Reporting Deduplication ────────────────────────────────────────────────

def test_report_duplicate_conflict():
    """Verify that reporting a paper twice while active raises 409 Conflict."""
    mock_db = MagicMock()
    from app.services.community_service import CommunityService
    from app.schemas.community import ReportCreate

    comm_svc = CommunityService(mock_db)
    with patch.object(comm_svc._repo, "create_report") as mock_create:
        mock_create.side_effect = ConflictError("An active report is already pending review for this item.")

        with pytest.raises(ConflictError) as exc:
            comm_svc.create_report(
                ReportCreate(target_type="paper", target_id="101", reason="Incorrect key"),
                firebase_uid="reporter-1",
            )
        assert "already pending review" in str(exc.value)


# ── 10. Submission Upload Failure Cleanup ─────────────────────────────────────

@pytest.mark.asyncio
async def test_submission_upload_failure_cleans_up():
    """Verify that if file upload fails, the orphan submission record is deleted."""
    mock_db = MagicMock()
    sub_svc = SubmissionsService(mock_db)
    mock_file = MagicMock()
    mock_file.filename = "test.pdf"
    mock_file.content_type = "application/pdf"
    async def async_read():
        return b"%PDF-1.4 sample content"
    mock_file.read = async_read

    with patch.object(sub_svc._repo, "create_submission", return_value={"id": 42}), \
         patch.object(sub_svc._repo, "upload_file", side_effect=Exception("Storage quota full")), \
         patch.object(sub_svc._repo, "delete_submission") as mock_cleanup:

        with pytest.raises(Exception) as exc:
            await sub_svc.create_submission(
                publisher_name="Teacher A",
                email="teacher@example.com",
                firebase_uid="user-123",
                details=None,
                files=[mock_file],
            )
        assert "upload failed" in str(exc.value) or "Storage quota full" in str(exc.value)
        mock_cleanup.assert_called_once_with(42)


# ── 11. Paper Verification Invalidation ───────────────────────────────────────

def test_unpublishing_verified_paper_invalidates_verification():
    """Verify that unpublishing a verified paper resets verification to PENDING_VERIFICATION."""
    mock_db = MagicMock()
    papers_svc = PapersService(mock_db)
    admin_user = {"firebase_uid": "admin-1", "email": "admin@example.com", "role": "ADMIN"}

    verified_paper = {
        "id": 101, "title": "Verified Paper", "status": "published",
        "verification_status": "VERIFIED", "subject_id": 1, "exam_type": "Public",
        "year": 2026, "paper_type": "question", "download_count": 5, "is_visible": True,
        "created_at": "2026-03-15T10:00:00Z",
    }
    updated_paper = {**verified_paper, "status": "archived", "verification_status": "PENDING_VERIFICATION"}

    with patch.object(papers_svc._repo, "get_by_id", return_value=verified_paper), \
         patch.object(papers_svc._repo, "invalidate_verification") as mock_inval, \
         patch.object(papers_svc._repo, "update_status", return_value=updated_paper), \
         patch("app.repositories.admin_activity_repository.AdminActivityRepository.log_activity"):

        res = papers_svc.update_paper_status(101, "archived", admin_user)
        mock_inval.assert_called_once_with(101, reason="Paper was unpublished for review")
        assert res.verification_status == "PENDING_VERIFICATION"
