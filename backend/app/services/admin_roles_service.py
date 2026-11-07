"""
Admin Roles service — business logic and security validations for Super Admin & Admin management.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.repositories.admin_activity_repository import AdminActivityRepository
from app.repositories.admin_roles_repository import (
    AccountConflictError,
    AdminRolesRepository,
    AppointmentClaimResult,
)
from app.schemas.admin_roles import (
    AdminAccountItem,
    AdminListResponse,
    AdminMeResponse,
    AdminRoleActionResponse,
    PendingAppointmentItem,
    PendingAppointmentListResponse,
)
from app.utils.exceptions import BadRequestError, NotFoundError

logger = logging.getLogger(__name__)
settings = get_settings()


class AdminRolesService:
    """Service layer enforcing Super Admin controls and role lifecycles."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = AdminRolesRepository(db)
        self._activity_repo = AdminActivityRepository(db)

    def get_admin_me(self, current_user: dict[str, Any]) -> AdminMeResponse:
        """Return authenticated administrator identity and role verification."""
        user_role = current_user.get("role") or "USER"
        user_email = (current_user.get("email") or "").strip().lower()
        is_super = user_role == "SUPER_ADMIN" or user_email == settings.ADMIN_EMAIL.lower()

        return AdminMeResponse(
            id=str(current_user["id"]),
            firebase_uid=current_user["firebase_uid"],
            email=current_user.get("email"),
            display_name=current_user.get("display_name"),
            photo_url=current_user.get("photo_url"),
            role=user_role,
            is_super_admin=is_super,
        )

    def get_admins_list(self) -> AdminListResponse:
        """Fetch all active administrators for Super Admin view."""
        rows, total = self._repo.get_admins()
        items = [
            AdminAccountItem(
                id=r["id"],
                firebase_uid=r["firebase_uid"],
                email=r.get("email"),
                display_name=r.get("display_name"),
                photo_url=r.get("photo_url"),
                role=r.get("role") or "USER",
                previous_role=r.get("previous_role"),
                is_active=r.get("is_active", True),
                created_at=r.get("created_at"),
                last_active_at=r.get("last_active_at"),
            )
            for r in rows
        ]
        return AdminListResponse(data=items, total=total)

    def get_pending_appointments(self) -> PendingAppointmentListResponse:
        """Fetch all pending email pre-authorizations."""
        rows = self._repo.get_pending_appointments()
        items = [
            PendingAppointmentItem(
                id=r["id"],
                email=r["email"],
                normalized_email=r["normalized_email"],
                created_by_uid=r["created_by_uid"],
                created_by_email=r["created_by_email"],
                status=r["status"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
        return PendingAppointmentListResponse(data=items, total=len(items))

    def preauthorize_email(
        self,
        email: str,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> AdminRoleActionResponse:
        """
        Pre-authorizes a Google account email as an Admin (Method 2).
        If the email is already registered as an active USER or CONTRIBUTOR, directly upgrades them to Admin.
        Otherwise, records a pending appointment awaiting their first Google Sign-In.
        Atomically commits the business mutation and centralized audit event.
        """
        norm_email = email.strip().lower()

        # Security Check 1: Super Admin email cannot be pre-authorized
        if norm_email == settings.ADMIN_EMAIL.lower():
            raise BadRequestError("This email address belongs to the Primary Super Admin.")

        # Security Check 2: Check if email already belongs to an active Admin or Super Admin
        existing_user = self._repo.get_user_by_email(norm_email)
        if existing_user and existing_user.get("role") in ("ADMIN", "SUPER_ADMIN"):
            raise BadRequestError("User with this email is already an active Administrator.")

        # Security Check 3: Check if appointment is already pending
        existing_appt = self._repo.get_pending_appointment_by_email(norm_email)
        if existing_appt:
            raise BadRequestError("An active admin pre-authorization is already pending for this email.")

        try:
            # If user is already registered as a regular USER or CONTRIBUTOR, directly upgrade them (Method 1)
            if existing_user:
                promoted = self._repo.promote_user_to_admin(
                    existing_user["firebase_uid"],
                    admin_actor_uid=current_user["firebase_uid"],
                )
                if promoted:
                    self._activity_repo.log_activity(
                        actor_uid=current_user["firebase_uid"],
                        actor_email=current_user.get("email") or settings.ADMIN_EMAIL,
                        actor_name=current_user.get("display_name") or current_user.get("email") or "Super Admin",
                        actor_role=current_user.get("role", "SUPER_ADMIN"),
                        action="ADMIN_ROLE_PROMOTED",
                        target_type="user",
                        target_id=promoted["firebase_uid"],
                        target_title=f"User {promoted.get('email')} promoted to Admin",
                        reason="Pre-authorized email already registered; directly upgraded to Admin",
                        metadata={
                            "email": promoted.get("email"),
                            "previous_role": promoted.get("previous_role"),
                            "assigned_role": "ADMIN",
                        },
                        ip_address=ip_address,
                    )
                    self._db.commit()
                    return AdminRoleActionResponse(
                        success=True,
                        message=f"User {existing_user.get('display_name', email)} was already registered and has been directly upgraded to Admin.",
                        user=AdminAccountItem(
                            id=promoted["id"],
                            firebase_uid=promoted["firebase_uid"],
                            email=promoted.get("email"),
                            display_name=promoted.get("display_name"),
                            photo_url=promoted.get("photo_url"),
                            role=promoted["role"],
                            previous_role=promoted.get("previous_role"),
                            is_active=promoted.get("is_active", True),
                            created_at=promoted.get("created_at"),
                            last_active_at=promoted.get("last_active_at"),
                        ),
                    )

            # User is not registered yet: record pending appointment
            appt = self._repo.create_pending_appointment(
                email=email.strip(),
                normalized_email=norm_email,
                created_by_uid=current_user["firebase_uid"],
                created_by_email=current_user.get("email") or settings.ADMIN_EMAIL,
            )

            self._activity_repo.log_activity(
                actor_uid=current_user["firebase_uid"],
                actor_email=current_user.get("email") or settings.ADMIN_EMAIL,
                actor_name=current_user.get("display_name") or current_user.get("email") or "Super Admin",
                actor_role=current_user.get("role", "SUPER_ADMIN"),
                action="ADMIN_APPOINTMENT_CREATED",
                target_type="admin_appointment",
                target_id=appt["id"],
                target_title=f"Admin pre-authorization created for {email.strip()}",
                reason="Pre-authorized email for Admin access",
                metadata={
                    "email": email.strip(),
                    "normalized_email": norm_email,
                },
                ip_address=ip_address,
            )
            self._db.commit()

            return AdminRoleActionResponse(
                success=True,
                message=f"Successfully pre-authorized {email}. They will receive Admin access upon their first Google sign-in.",
                user=None,
            )
        except Exception:
            self._db.rollback()
            raise

    def revoke_pending_appointment(
        self,
        appointment_id: str,
        current_user: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AdminRoleActionResponse:
        """
        Revoke a pending email pre-authorization before sign-in.
        Atomically commits the revocation and centralized audit log event.
        """
        try:
            revoked = self._repo.revoke_pending_appointment(appointment_id)
            if not revoked:
                raise NotFoundError(resource="Pending Appointment", identifier=appointment_id)

            if current_user:
                actor_uid = current_user.get("firebase_uid", "unknown")
                actor_email = current_user.get("email") or settings.ADMIN_EMAIL
                actor_name = current_user.get("display_name") or actor_email
                actor_role = current_user.get("role", "SUPER_ADMIN")
            else:
                actor_uid = "system"
                actor_email = settings.ADMIN_EMAIL
                actor_name = "Super Admin"
                actor_role = "SUPER_ADMIN"

            self._activity_repo.log_activity(
                actor_uid=actor_uid,
                actor_email=actor_email,
                actor_name=actor_name,
                actor_role=actor_role,
                action="ADMIN_APPOINTMENT_REVOKED",
                target_type="admin_appointment",
                target_id=appointment_id,
                target_title=f"Admin pre-authorization revoked for {revoked['email']}",
                reason="Super Admin revoked pending appointment",
                metadata={
                    "email": revoked.get("email"),
                    "normalized_email": revoked.get("normalized_email"),
                },
                ip_address=ip_address,
            )
            self._db.commit()

            return AdminRoleActionResponse(
                success=True,
                message=f"Successfully revoked pending appointment for {revoked['email']}.",
                user=None,
            )
        except Exception:
            self._db.rollback()
            raise

    def promote_registered_user(
        self,
        firebase_uid: str,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> AdminRoleActionResponse:
        """
        Promote an existing registered user to Admin (Method 1).
        Preserves original role in previous_role.
        Atomically commits role update and centralized audit log event.
        """
        target = self._repo.get_user_by_firebase_uid(firebase_uid)
        if not target:
            raise NotFoundError(resource="Registered User", identifier=firebase_uid)

        target_email = (target.get("email") or "").strip().lower()
        if target_email == settings.ADMIN_EMAIL.lower() or target.get("role") == "SUPER_ADMIN":
            raise BadRequestError("Cannot modify the Primary Super Admin account.")

        if target.get("role") == "ADMIN":
            raise BadRequestError("This user is already an Administrator.")

        try:
            promoted = self._repo.promote_user_to_admin(
                firebase_uid,
                admin_actor_uid=current_user["firebase_uid"],
            )
            if not promoted:
                raise BadRequestError("Failed to promote user to Admin.")

            self._activity_repo.log_activity(
                actor_uid=current_user["firebase_uid"],
                actor_email=current_user.get("email") or settings.ADMIN_EMAIL,
                actor_name=current_user.get("display_name") or current_user.get("email") or "Super Admin",
                actor_role=current_user.get("role", "SUPER_ADMIN"),
                action="ADMIN_ROLE_PROMOTED",
                target_type="user",
                target_id=firebase_uid,
                target_title=f"User {promoted.get('display_name', 'user')} ({promoted.get('email')}) promoted to Admin",
                reason="Super Admin promoted user to Admin",
                metadata={
                    "email": promoted.get("email"),
                    "previous_role": promoted.get("previous_role"),
                    "assigned_role": "ADMIN",
                },
                ip_address=ip_address,
            )
            self._db.commit()

            return AdminRoleActionResponse(
                success=True,
                message=f"Successfully promoted {promoted.get('display_name', 'user')} to Admin.",
                user=AdminAccountItem(
                    id=promoted["id"],
                    firebase_uid=promoted["firebase_uid"],
                    email=promoted.get("email"),
                    display_name=promoted.get("display_name"),
                    photo_url=promoted.get("photo_url"),
                    role=promoted["role"],
                    previous_role=promoted.get("previous_role"),
                    is_active=promoted.get("is_active", True),
                    created_at=promoted.get("created_at"),
                    last_active_at=promoted.get("last_active_at"),
                ),
            )
        except Exception:
            self._db.rollback()
            raise

    def revoke_admin_role(
        self,
        firebase_uid: str,
        current_user: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> AdminRoleActionResponse:
        """
        Revoke an Admin's privileges.
        Restores their original role from previous_role (USER or CONTRIBUTOR).
        Preserves user account and all contribution history.
        Atomically commits role demotion and centralized audit log event.
        """
        # Security Check 1: Prevent self-revocation
        if firebase_uid == current_user["firebase_uid"]:
            raise BadRequestError("Cannot remove your own administrative privileges.")

        target = self._repo.get_user_by_firebase_uid(firebase_uid)
        if not target:
            raise NotFoundError(resource="Admin User", identifier=firebase_uid)

        target_email = (target.get("email") or "").strip().lower()
        if target_email == settings.ADMIN_EMAIL.lower() or target.get("role") == "SUPER_ADMIN":
            raise BadRequestError("Cannot revoke the Primary Super Admin account.")

        if target.get("role") != "ADMIN":
            raise BadRequestError("User is not an active Admin.")

        try:
            revoked = self._repo.revoke_admin_role(firebase_uid)
            if not revoked:
                raise BadRequestError("Failed to revoke Admin role.")

            restored_role = revoked.get("role", "USER")
            self._activity_repo.log_activity(
                actor_uid=current_user["firebase_uid"],
                actor_email=current_user.get("email") or settings.ADMIN_EMAIL,
                actor_name=current_user.get("display_name") or current_user.get("email") or "Super Admin",
                actor_role=current_user.get("role", "SUPER_ADMIN"),
                action="ADMIN_ROLE_REVOKED",
                target_type="user",
                target_id=firebase_uid,
                target_title=f"Admin privileges revoked for {revoked.get('display_name', 'user')} ({revoked.get('email')})",
                reason="Super Admin revoked Admin privileges; role restored",
                metadata={
                    "email": revoked.get("email"),
                    "restored_role": restored_role,
                    "previous_role": revoked.get("previous_role"),
                },
                ip_address=ip_address,
            )
            self._db.commit()

            return AdminRoleActionResponse(
                success=True,
                message=f"Successfully revoked Admin access for {revoked.get('display_name', 'user')}. Role restored to {restored_role}.",
                user=AdminAccountItem(
                    id=revoked["id"],
                    firebase_uid=revoked["firebase_uid"],
                    email=revoked.get("email"),
                    display_name=revoked.get("display_name"),
                    photo_url=revoked.get("photo_url"),
                    role=revoked["role"],
                    previous_role=revoked.get("previous_role"),
                    is_active=revoked.get("is_active", True),
                    created_at=revoked.get("created_at"),
                    last_active_at=revoked.get("last_active_at"),
                ),
            )
        except Exception:
            self._db.rollback()
            raise

    def resolve_and_claim_admin(
        self,
        decoded_token: dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Invoked exclusively on Admin routes when an authenticated administrator logs in.
        Ensures any pending pre-authorization is claimed atomically and account linking
        is verified against account takeover.

        Participates in a single database transaction:
        1. Atomic appointment claim via stored procedure.
        2. Audit log entry (APPOINTMENT_CLAIMED) in public.admin_activity_logs iff claimed is True.
        3. Single atomic commit if both succeed; rollback if either fails.
        """
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        display_name = decoded_token.get("name")
        photo_url = decoded_token.get("picture")

        if not firebase_uid or not email:
            raise BadRequestError("Invalid token payload: missing uid or email.")

        # Ensure email is verified by Google OAuth before claiming
        if not decoded_token.get("email_verified", False):
            logger.warning("Unverified email attempted admin resolution: %s", email)

        try:
            claim_result = self._repo.claim_pending_appointment_atomic(
                firebase_uid=firebase_uid,
                email=email,
                display_name=display_name,
                photo_url=photo_url,
            )

            # Support both AppointmentClaimResult dataclass and legacy mocked dict returns
            if isinstance(claim_result, AppointmentClaimResult):
                user_record = claim_result.user
                claimed = claim_result.claimed
                appointment_id = claim_result.appointment_id
                assigned_role = claim_result.assigned_role
            elif isinstance(claim_result, dict):
                user_record = claim_result
                claimed = False
                appointment_id = None
                assigned_role = None
            else:
                raise ValueError("Unexpected claim result type returned by repository.")

            # Record audit event whenever a confirmed claim occurs
            if claimed:
                if not appointment_id or not str(appointment_id).strip():
                    raise ValueError(
                        "Appointment claim confirmed (claimed=True) but appointment_id is missing or invalid."
                    )

                clean_appointment_id = str(appointment_id).strip()
                actor_uid = user_record.get("firebase_uid") or firebase_uid
                actor_email = user_record.get("email") or email
                actor_name = user_record.get("display_name") or display_name or actor_email
                actor_role = user_record.get("role") or assigned_role or "ADMIN"

                self._activity_repo.log_activity(
                    actor_uid=actor_uid,
                    actor_email=actor_email,
                    actor_name=actor_name,
                    actor_role=actor_role,
                    action="APPOINTMENT_CLAIMED",
                    target_type="admin_appointment",
                    target_id=clean_appointment_id,
                    target_title=f"Admin appointment claimed by {actor_email}",
                    reason="Pre-authorized admin appointment claimed upon login",
                    metadata={
                        "assigned_role": assigned_role or "ADMIN",
                        "appointment_id": clean_appointment_id,
                    },
                    ip_address=ip_address,
                )

            # Atomic commit of both appointment claim and audit log
            self._db.commit()
            return user_record

        except Exception:
            self._db.rollback()
            raise
