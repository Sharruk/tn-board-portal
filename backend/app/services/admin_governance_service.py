"""
Admin Governance service — business logic for delegated admin additions,
two-person removal approvals, and verified teacher status management.
Matches the live Supabase schema established in Migration 028.
"""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.repositories.admin_activity_repository import AdminActivityRepository
from app.repositories.admin_governance_repository import AdminGovernanceRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.admin_governance import (
    AdminAddRequest,
    AdminGovernanceListResponse,
    AdminGovernanceRequestResponse,
    AdminRemovalRequestCreate,
)
from app.utils.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)
settings = get_settings()

MONTHLY_ADMIN_ADDITION_QUOTA = 3


class AdminGovernanceService:
    """Service managing admin governance workflows."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AdminGovernanceRepository(db)
        self._user_repo = UserProfileRepository(db)
        self._activity_repo = AdminActivityRepository(db)

    # ── Admin Addition ────────────────────────────────────────────────────────

    def add_admin(self, req: AdminAddRequest, initiator: dict[str, Any]) -> dict[str, Any]:
        """
        Add a trusted teacher/community member as Admin.

        Allowed callers:
          - SUPER_ADMIN (unrestricted)
          - Verified Admin / Verified Teacher (quota: 3 additions/month)
        """
        initiator_role = initiator.get("role", "USER")
        is_verified_teacher = bool(initiator.get("is_verified_teacher", False))

        is_super = initiator_role == "SUPER_ADMIN" or initiator.get("email") == settings.ADMIN_EMAIL
        can_add = is_super or (initiator_role == "ADMIN" and is_verified_teacher)

        if not can_add:
            raise ForbiddenError("Only Super Admin or Super-Admin-Verified Teachers can add new Administrators.")

        # Concurrency safety: acquire transaction-level advisory lock on initiator
        if not is_super:
            self._repo.acquire_initiator_lock(initiator["firebase_uid"])
            monthly_count = self._repo.count_monthly_additions(initiator["firebase_uid"])
            if monthly_count >= MONTHLY_ADMIN_ADDITION_QUOTA:
                raise ValidationError(
                    f"Monthly quota reached ({MONTHLY_ADMIN_ADDITION_QUOTA} admins/month). "
                    "Contact Super Administrator for quota extension."
                )

        target_email = req.email.strip().lower()
        target_name = req.display_name.strip() if req.display_name else None

        # Look up or create target user
        user = self._user_repo.get_by_email(target_email)
        if user:
            if user.get("role") in ("ADMIN", "SUPER_ADMIN"):
                raise ValidationError(f"User {target_email} is already an Administrator.")
            target_uid = user["firebase_uid"]
            target_name = target_name or user.get("display_name") or target_email.split("@")[0]
            self._user_repo.update_role(
                firebase_uid=target_uid,
                new_role="ADMIN",
                admin_added_by_uid=initiator["firebase_uid"],
            )
        else:
            # Pre-provision user placeholder with role=ADMIN
            target_uid = f"pending_{target_email}"
            target_name = target_name or target_email.split("@")[0]
            user = self._user_repo.upsert_user(
                firebase_uid=target_uid,
                email=target_email,
                display_name=target_name,
                role="ADMIN",
                admin_added_by_uid=initiator["firebase_uid"],
            )

        initiator_name = initiator.get("display_name") or initiator.get("email")
        initiator_email = initiator.get("email") or "system@hungrylearner.internal"

        # Record governance request log as completed/approved
        gov_req = self._repo.create_request(
            request_type="admin_addition",
            target_user_uid=target_uid,
            target_email=target_email,
            target_name=target_name,
            initiated_by_uid=initiator["firebase_uid"],
            initiated_by_email=initiator_email,
            initiated_by_name=initiator_name,
            reason=req.reason or "Added as trusted Admin",
            status="approved",
            decision_notes="Direct addition by authorized administrator",
        )

        # Audit log
        self._activity_repo.log_activity(
            actor_uid=initiator["firebase_uid"],
            actor_email=initiator_email,
            actor_name=initiator_name,
            actor_role=initiator_role,
            action="admin_add",
            target_type="user",
            target_id=target_uid,
            target_title=target_name or target_email,
            reason=req.reason,
            metadata={"email": target_email, "added_by": initiator_name, "request_id": gov_req["id"]},
        )

        return {
            "success": True,
            "message": f"Successfully added {target_email} as Administrator.",
            "user": {
                "firebase_uid": target_uid,
                "email": target_email,
                "role": "ADMIN",
                "display_name": target_name,
            },
        }

    # ── Admin Removal Request ─────────────────────────────────────────────────

    def request_admin_removal(
        self,
        req: AdminRemovalRequestCreate,
        initiator: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Request removal of an Admin.

        Allowed callers:
          - SUPER_ADMIN (unilateral immediate removal)
          - Verified Admin / Verified Teacher (enters two-person approval workflow)
        """
        initiator_role = initiator.get("role", "USER")
        is_verified_teacher = bool(initiator.get("is_verified_teacher", False))
        is_super = initiator_role == "SUPER_ADMIN" or initiator.get("email") == settings.ADMIN_EMAIL
        can_govern = is_super or (initiator_role == "ADMIN" and is_verified_teacher)

        if not can_govern:
            raise ForbiddenError("Only Super Admin or Super-Admin-Verified Teachers can request Admin removal.")

        target_uid = req.target_uid
        target = self._user_repo.get_by_firebase_uid(target_uid)
        if not target:
            raise NotFoundError(resource="User", identifier=target_uid)

        # Cannot remove Super Admin
        if target.get("email") == settings.ADMIN_EMAIL or target.get("role") == "SUPER_ADMIN":
            raise ForbiddenError("Cannot remove the Super Administrator.")

        # Target must actually be an admin
        if target.get("role") not in ("ADMIN", "SUPER_ADMIN"):
            raise ValidationError("Target user is not an Administrator.")

        # Initiator cannot remove self
        if initiator["firebase_uid"] == target_uid:
            raise ValidationError("You cannot request the removal of your own Administrator account.")

        # Check if already pending removal
        existing_pending = self._repo.get_pending_removal(target_uid)
        if existing_pending:
            raise ConflictError("A removal request is already pending for this Administrator.")

        initiator_name = initiator.get("display_name") or initiator.get("email")
        initiator_email = initiator.get("email") or "system@hungrylearner.internal"

        # If Super Admin, execute immediate unilateral removal
        if is_super:
            self._user_repo.update_role(firebase_uid=target_uid, new_role="USER")
            self._user_repo.update_verified_teacher(firebase_uid=target_uid, is_verified=False)
            self._user_repo.update_governance_status(firebase_uid=target_uid, governance_status="removed")

            # Audit log
            self._activity_repo.log_activity(
                actor_uid=initiator["firebase_uid"],
                actor_email=initiator_email,
                actor_name=initiator_name,
                actor_role=initiator_role,
                action="admin_remove_direct",
                target_type="user",
                target_id=target_uid,
                target_title=target.get("display_name") or target.get("email"),
                reason=req.reason,
                metadata={"executor": "SUPER_ADMIN"},
            )

            return {
                "success": True,
                "message": f"Administrator {target.get('email')} has been revoked by Super Admin.",
                "status": "REMOVED",
            }

        # Otherwise, initiate two-person approval request
        gov_req = self._repo.create_request(
            request_type="admin_removal",
            target_user_uid=target_uid,
            target_email=target.get("email") or "",
            target_name=target.get("display_name") or target.get("email") or "Admin",
            initiated_by_uid=initiator["firebase_uid"],
            initiated_by_email=initiator_email,
            initiated_by_name=initiator_name,
            reason=req.reason,
            status="pending",
        )

        # Update target governance status
        self._user_repo.update_governance_status(firebase_uid=target_uid, governance_status="pending_removal")

        # Audit log
        self._activity_repo.log_activity(
            actor_uid=initiator["firebase_uid"],
            actor_email=initiator_email,
            actor_name=initiator_name,
            actor_role=initiator_role,
            action="admin_removal_requested",
            target_type="user",
            target_id=target_uid,
            target_title=target.get("display_name") or target.get("email"),
            reason=req.reason,
            metadata={"request_id": gov_req["id"]},
        )

        return {
            "success": True,
            "message": "Admin removal request submitted. Pending second Verified Teacher or Super Admin approval.",
            "request": gov_req,
        }

    def direct_remove_admin(
        self,
        target_uid: str,
        reason: str,
        initiator: dict[str, Any],
    ) -> dict[str, Any]:
        """Convenience method for direct removal of an Administrator by Super Admin."""
        return self.request_admin_removal(
            AdminRemovalRequestCreate(target_uid=target_uid, reason=reason),
            initiator=initiator,
        )

    # ── Admin Removal Approval / Rejection ────────────────────────────────────

    def process_removal_approval(
        self,
        request_id: str,
        action: str,  # 'APPROVED' or 'REJECTED'
        approver: dict[str, Any],
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Approve or reject a pending admin removal request.

        Collusion & Integrity rules:
          - Approver must be Verified Teacher or Super Admin.
          - Approver cannot be the initiator (two-person rule).
          - Approver cannot be the target (self-preservation rule).
          - Super Admin can approve/reject any request.
        """
        req = self._repo.get_by_id(request_id)
        if not req:
            raise NotFoundError(resource="GovernanceRequest", identifier=request_id)

        if req["status"] != "pending":
            raise ValidationError(f"Request is not pending approval (current status: {req['status']}).")

        approver_uid = approver["firebase_uid"]

        # Target cannot approve or reject their own removal
        if approver_uid == req["target_user_uid"]:
            raise ForbiddenError("The target Administrator cannot participate in their own removal decision.")

        approver_role = approver.get("role", "USER")
        is_verified_teacher = bool(approver.get("is_verified_teacher", False))
        is_super = approver_role == "SUPER_ADMIN" or approver.get("email") == settings.ADMIN_EMAIL
        can_govern = is_super or (approver_role == "ADMIN" and is_verified_teacher)

        if not can_govern:
            raise ForbiddenError("Only Super Admin or Super-Admin-Verified Teachers can participate in removal decisions.")

        # Two-person rule: Initiator cannot approve
        if approver_uid == req["initiated_by_uid"] and not is_super:
            raise ForbiddenError("You cannot approve a removal request you initiated.")

        approver_name = approver.get("display_name") or approver.get("email")
        approver_email = approver.get("email") or "system@hungrylearner.internal"
        target_uid = req["target_user_uid"]

        act_upper = action.strip().upper()
        if act_upper == "APPROVED":
            # Demote target admin to USER and revoke verified teacher status
            self._user_repo.update_role(firebase_uid=target_uid, new_role="USER")
            self._user_repo.update_verified_teacher(firebase_uid=target_uid, is_verified=False)
            self._user_repo.update_governance_status(firebase_uid=target_uid, governance_status="removed")

            updated_req = self._repo.update_request_status(
                request_id=request_id,
                status="approved",
                second_approver_uid=approver_uid,
                second_approver_email=approver_email,
                second_approver_name=approver_name,
                decision_notes=note,
            )

            # Audit log
            self._activity_repo.log_activity(
                actor_uid=approver_uid,
                actor_email=approver_email,
                actor_name=approver_name,
                actor_role=approver_role,
                action="admin_removal_approved",
                target_type="user",
                target_id=target_uid,
                target_title=req.get("target_name") or req.get("target_email"),
                reason=note,
                metadata={
                    "request_id": request_id,
                    "initiated_by": req.get("initiated_by_name"),
                },
            )

            return {
                "success": True,
                "message": f"Administrator removal approved. {req.get('target_email')} has been revoked.",
                "request": updated_req,
            }

        elif act_upper == "REJECTED":
            # Restore active governance status
            self._user_repo.update_governance_status(firebase_uid=target_uid, governance_status="active")

            updated_req = self._repo.update_request_status(
                request_id=request_id,
                status="rejected",
                second_approver_uid=approver_uid,
                second_approver_email=approver_email,
                second_approver_name=approver_name,
                decision_notes=note,
            )

            # Audit log
            self._activity_repo.log_activity(
                actor_uid=approver_uid,
                actor_email=approver_email,
                actor_name=approver_name,
                actor_role=approver_role,
                action="admin_removal_rejected",
                target_type="user",
                target_id=target_uid,
                target_title=req.get("target_name") or req.get("target_email"),
                reason=note,
                metadata={
                    "request_id": request_id,
                    "initiated_by": req.get("initiated_by_name"),
                },
            )

            return {
                "success": True,
                "message": f"Administrator removal request rejected for {req.get('target_email')}.",
                "request": updated_req,
            }
        else:
            raise ValidationError(f"Invalid action '{action}'. Must be APPROVED or REJECTED.")

    # ── List Requests ─────────────────────────────────────────────────────────

    def list_governance_requests(
        self,
        status: Optional[str] = None,
        request_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AdminGovernanceListResponse:
        """List governance requests."""
        rows, total = self._repo.list_requests(
            status=status,
            request_type=request_type,
            limit=limit,
            offset=offset,
        )
        return AdminGovernanceListResponse(
            requests=[AdminGovernanceRequestResponse(**r) for r in rows],
            total=total,
        )

    # ── Super Admin: Toggle Verified Teacher ──────────────────────────────────

    def toggle_verified_teacher(
        self,
        target_uid: str,
        is_verified: bool,
        current_user: dict[str, Any],
    ) -> dict[str, Any]:
        """Grant or revoke Verified Teacher status (Super Admin only)."""
        target = self._user_repo.get_by_firebase_uid(target_uid)
        if not target:
            raise NotFoundError(resource="User", identifier=target_uid)

        if target.get("role") not in ("ADMIN", "SUPER_ADMIN"):
            raise ValidationError("Only Administrators can be granted Verified Teacher status.")

        updated = self._user_repo.update_verified_teacher(
            firebase_uid=target_uid,
            is_verified=is_verified,
            verified_by_uid=current_user["firebase_uid"],
        )

        # Audit log
        action = "teacher_verification_granted" if is_verified else "teacher_verification_revoked"
        admin_name = current_user.get("display_name") or current_user.get("email")
        admin_email = current_user.get("email") or "system@hungrylearner.internal"
        self._activity_repo.log_activity(
            actor_uid=current_user["firebase_uid"],
            actor_email=admin_email,
            actor_name=admin_name,
            actor_role=current_user.get("role", "SUPER_ADMIN"),
            action=action,
            target_type="user",
            target_id=target_uid,
            target_title=target.get("display_name") or target.get("email"),
            metadata={"is_verified_teacher": is_verified, "admin_uid": target_uid},
        )

        status_text = "granted" if is_verified else "revoked"
        return {
            "success": True,
            "message": f"Verified Teacher status {status_text} for {target.get('email')}.",
            "user": updated,
        }
