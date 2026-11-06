"""
Admin Roles repository — PostgreSQL data access for Super Admin & Admin management.
"""

from dataclasses import dataclass
import json
import logging
from typing import Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class AppointmentClaimResult:
    """Structured result returned by claim_pending_appointment_atomic."""
    user: dict[str, Any]
    claimed: bool
    appointment_id: Optional[str] = None
    assigned_role: Optional[str] = None


class AccountConflictError(Exception):
    """Raised when an email is already registered under a different account identifier."""
    pass


def _is_account_conflict_exception(exc: Exception) -> bool:
    """
    Determine if an exception represents an ACCOUNT_CONFLICT error raised by PostgreSQL RPC.
    Requires PostgreSQL SQLSTATE P0001 AND the specific 'ACCOUNT_CONFLICT:' diagnostic message.
    Inspects DBAPI exception attributes on exc.orig or exc directly.
    Fails closed if the exception does not exhibit this verified structure.
    """
    if isinstance(exc, AccountConflictError):
        return True

    # Inspect the underlying DBAPI driver error (e.g. from SQLAlchemy's exc.orig) or exc directly
    for target in (getattr(exc, "orig", None), exc):
        if target is None:
            continue

        # Extract PostgreSQL error code (SQLSTATE)
        pgcode = getattr(target, "pgcode", None)
        if pgcode is None:
            pgcode = getattr(target, "sqlstate", None)

        # PL/pgSQL RAISE EXCEPTION produces SQLSTATE P0001
        if not pgcode or str(pgcode).strip().upper() != "P0001":
            continue

        # Check structured driver diagnostic message (psycopg2 Error.diag.message_primary)
        diag = getattr(target, "diag", None)
        if diag is not None:
            primary = getattr(diag, "message_primary", None)
            if primary and str(primary).strip().startswith("ACCOUNT_CONFLICT:"):
                return True

        # Fallback for driver representations where diag is unavailable but target is a DBAPI error with P0001
        # Inspect target's message (which comes from PostgreSQL server, NOT SQLAlchemy parameter dumps)
        target_str = str(target).strip()
        if target_str.startswith("ACCOUNT_CONFLICT:") or "\nACCOUNT_CONFLICT:" in target_str or target_str.startswith("psycopg2.errors.RaiseException: ACCOUNT_CONFLICT:"):
            # Guard: ensure we only match if target is not the outer SQLAlchemy exception that could contain params
            if target is not exc or not hasattr(exc, "statement"):
                return True

    return False


class AdminRolesRepository:
    """Data access layer for Admin Role Management and Pre-authorizations."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_admins(self) -> tuple[List[dict[str, Any]], int]:
        """Fetch all active administrators (Super Admin and Admins)."""
        sql = """
            SELECT
                u.id,
                u.firebase_uid,
                u.email,
                u.display_name,
                u.photo_url,
                u.role,
                CASE
                    WHEN EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = 'users' AND column_name = 'previous_role'
                    ) THEN u.previous_role
                    ELSE NULL
                END AS previous_role,
                u.is_active,
                u.created_at,
                u.last_active_at
            FROM users u
            WHERE u.role IN ('ADMIN', 'SUPER_ADMIN')
            ORDER BY
                CASE WHEN u.role = 'SUPER_ADMIN' THEN 0 ELSE 1 END,
                u.created_at ASC
        """
        try:
            rows = self._db.execute(text(sql)).fetchall()
        except Exception as exc:
            # Resilient fallback if previous_role column check fails
            self._db.rollback()
            fallback_sql = """
                SELECT id, firebase_uid, email, display_name, photo_url, role, NULL AS previous_role, is_active, created_at, last_active_at
                FROM users
                WHERE role IN ('ADMIN', 'SUPER_ADMIN')
                ORDER BY CASE WHEN role = 'SUPER_ADMIN' THEN 0 ELSE 1 END, created_at ASC
            """
            rows = self._db.execute(text(fallback_sql)).fetchall()

        items = []
        for r in rows:
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            items.append(d)
        return items, len(items)

    def get_pending_appointments(self) -> List[dict[str, Any]]:
        """Fetch all active pending email pre-authorizations."""
        sql = """
            SELECT id, email, normalized_email, created_by_uid, created_by_email, status, created_at
            FROM pending_admin_appointments
            WHERE status = 'pending'
            ORDER BY created_at DESC
        """
        try:
            rows = self._db.execute(text(sql)).fetchall()
            items = []
            for r in rows:
                d = dict(r._mapping)
                d["id"] = str(d["id"])
                items.append(d)
            return items
        except Exception as exc:
            self._db.rollback()
            logger.warning("Failed to fetch pending_admin_appointments (table may be pending migration): %s", exc)
            return []

    def get_pending_appointment_by_email(self, normalized_email: str) -> Optional[dict[str, Any]]:
        """Fetch active pending appointment by normalized email."""
        sql = """
            SELECT id, email, normalized_email, created_by_uid, created_by_email, status, created_at
            FROM pending_admin_appointments
            WHERE normalized_email = :norm_email AND status = 'pending'
            LIMIT 1
        """
        try:
            row = self._db.execute(text(sql), {"norm_email": normalized_email}).fetchone()
            if not row:
                return None
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d
        except Exception as exc:
            self._db.rollback()
            logger.warning("Error checking pending appointment: %s", exc)
            return None

    def create_pending_appointment(
        self,
        email: str,
        normalized_email: str,
        created_by_uid: str,
        created_by_email: str,
    ) -> dict[str, Any]:
        """Create a new pending admin pre-authorization."""
        sql = """
            INSERT INTO pending_admin_appointments (
                email, normalized_email, created_by_uid, created_by_email, status, created_at, updated_at
            )
            VALUES (
                :email, :norm_email, :creator_uid, :creator_email, 'pending', NOW(), NOW()
            )
            RETURNING id, email, normalized_email, created_by_uid, created_by_email, status, created_at
        """
        res = self._db.execute(
            text(sql),
            {
                "email": email,
                "norm_email": normalized_email,
                "creator_uid": created_by_uid,
                "creator_email": created_by_email,
            },
        )
        row = res.fetchone()
        if not row:
            raise RuntimeError("Failed to create pending admin appointment.")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def revoke_pending_appointment(self, appointment_id: str) -> Optional[dict[str, Any]]:
        """Revoke a pending admin pre-authorization before sign-in."""
        sql = """
            UPDATE pending_admin_appointments
            SET status = 'revoked', updated_at = NOW()
            WHERE id = :id AND status = 'pending'
            RETURNING id, email, normalized_email, created_by_uid, created_by_email, status, created_at
        """
        res = self._db.execute(text(sql), {"id": appointment_id})
        row = res.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[dict[str, Any]]:
        """Fetch user record by Firebase UID."""
        sql = """
            SELECT id, firebase_uid, email, display_name, photo_url, role, is_active, created_at, last_active_at
            FROM users
            WHERE firebase_uid = :uid
        """
        row = self._db.execute(text(sql), {"uid": firebase_uid}).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def get_user_by_email(self, email: str) -> Optional[dict[str, Any]]:
        """Fetch user record by normalized email."""
        sql = """
            SELECT id, firebase_uid, email, display_name, photo_url, role, is_active, created_at, last_active_at
            FROM users
            WHERE LOWER(email) = LOWER(:email)
            LIMIT 1
        """
        row = self._db.execute(text(sql), {"email": email.strip().lower()}).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def promote_user_to_admin(self, firebase_uid: str, admin_actor_uid: str) -> Optional[dict[str, Any]]:
        """
        Promote an existing registered user to Admin.
        Atomically saves original role in previous_role and sets role = 'ADMIN'.
        Only operates on users whose role is NOT already ADMIN or SUPER_ADMIN.
        Uses a nested savepoint to isolate primary update from legacy column fallback.
        """
        primary_sql = """
            UPDATE users
            SET
                previous_role = role,
                role = 'ADMIN',
                updated_at = NOW()
            WHERE firebase_uid = :uid
              AND role NOT IN ('ADMIN', 'SUPER_ADMIN')
            RETURNING id, firebase_uid, email, display_name, photo_url, role, previous_role, is_active, created_at, last_active_at
        """
        try:
            with self._db.begin_nested():
                res = self._db.execute(text(primary_sql), {"uid": firebase_uid})
                row = res.fetchone()
                if not row:
                    return None
                d = dict(row._mapping)
                d["id"] = str(d["id"])
                return d
        except Exception:
            # Resilient fallback if previous_role column does not exist yet in legacy environment
            fallback_sql = """
                UPDATE users
                SET
                    role = 'ADMIN',
                    updated_at = NOW()
                WHERE firebase_uid = :uid
                  AND role NOT IN ('ADMIN', 'SUPER_ADMIN')
                RETURNING id, firebase_uid, email, display_name, photo_url, role, NULL AS previous_role, is_active, created_at, last_active_at
            """
            res = self._db.execute(text(fallback_sql), {"uid": firebase_uid})
            row = res.fetchone()
            if not row:
                return None
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d

    def revoke_admin_role(self, firebase_uid: str) -> Optional[dict[str, Any]]:
        """
        Revoke an Admin's privileges.
        Atomically restores their original role from previous_role (falling back to 'USER')
        and clears previous_role.
        Only operates on users whose role is currently 'ADMIN'.
        Uses a nested savepoint to isolate primary update from legacy column fallback.
        """
        primary_sql = """
            UPDATE users
            SET
                role = COALESCE(previous_role, 'USER'),
                previous_role = NULL,
                updated_at = NOW()
            WHERE firebase_uid = :uid
              AND role = 'ADMIN'
            RETURNING id, firebase_uid, email, display_name, photo_url, role, previous_role, is_active, created_at, last_active_at
        """
        try:
            with self._db.begin_nested():
                res = self._db.execute(text(primary_sql), {"uid": firebase_uid})
                row = res.fetchone()
                if not row:
                    return None
                d = dict(row._mapping)
                d["id"] = str(d["id"])
                return d
        except Exception:
            # Resilient fallback if previous_role column is not present
            fallback_sql = """
                UPDATE users
                SET
                    role = 'USER',
                    updated_at = NOW()
                WHERE firebase_uid = :uid
                  AND role = 'ADMIN'
                RETURNING id, firebase_uid, email, display_name, photo_url, role, NULL AS previous_role, is_active, created_at, last_active_at
            """
            res = self._db.execute(text(fallback_sql), {"uid": firebase_uid})
            row = res.fetchone()
            if not row:
                return None
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d

    def claim_pending_appointment_atomic(
        self,
        firebase_uid: str,
        email: str,
        display_name: Optional[str],
        photo_url: Optional[str],
    ) -> AppointmentClaimResult:
        """
        Atomically claims any active pending appointment for this verified email.
        Executes the claim_pending_admin_appointment stored procedure inside a
        savepoint (nested transaction).

        CRITICAL ARCHITECTURAL INVARIANTS:
        1. This repository method DOES NOT call self._db.commit() or self._db.rollback().
           The calling service (AdminRolesService) owns the transaction so that audit
           logging (APPOINTMENT_CLAIMED) and the claim mutation participate in the
           exact same database transaction.
        2. Database errors (e.g. UndefinedColumn, InsufficientPrivilege, OperationalError,
           UndefinedFunction) propagate immediately without fallback, rolling back the
           savepoint and alerting the calling service to abort the outer transaction.
        3. Account identity conflicts (PostgreSQL RAISE EXCEPTION 'ACCOUNT_CONFLICT...')
           are converted to AccountConflictError mapping to HTTP 409 Conflict.
        """
        rpc_sql = "SELECT claim_pending_admin_appointment(:uid, :email, :name, :photo)"
        try:
            with self._db.begin_nested():
                res = self._db.execute(
                    text(rpc_sql),
                    {
                        "uid": firebase_uid,
                        "email": email,
                        "name": display_name,
                        "photo": photo_url,
                    },
                )
                row = res.fetchone()
                if not row or not row[0]:
                    raise RuntimeError("claim_pending_admin_appointment RPC returned empty result.")

                payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])

                if isinstance(payload, dict) and "user" in payload and isinstance(payload["user"], dict):
                    # Migration 031 envelope format:
                    user_data = payload["user"]

                    # 1. Strict boolean validation on 'claimed' field
                    if "claimed" not in payload:
                        raise ValueError(f"RPC claim response envelope missing required 'claimed' field: {payload}")
                    raw_claimed = payload["claimed"]
                    if type(raw_claimed) is not bool:
                        raise ValueError(
                            f"RPC claim response 'claimed' field must be an explicit boolean, got {type(raw_claimed).__name__}: {raw_claimed!r}"
                        )
                    claimed = raw_claimed

                    # 2. Strict Appointment ID consistency and type validation with 'claimed'
                    raw_appt_id = payload.get("appointment_id")
                    if claimed is True:
                        if raw_appt_id is None:
                            raise ValueError(
                                f"RPC claim response claimed=True requires valid non-null appointment_id, got: {raw_appt_id!r}"
                            )
                        if type(raw_appt_id) is not str:
                            raise ValueError(
                                f"RPC claim response claimed=True requires appointment_id of type str, got {type(raw_appt_id).__name__}: {raw_appt_id!r}"
                            )
                        clean_appt_id = raw_appt_id.strip()
                        if not clean_appt_id:
                            raise ValueError(
                                f"RPC claim response claimed=True requires non-empty appointment_id, got: {raw_appt_id!r}"
                            )
                        appointment_id = clean_appt_id
                    else:
                        # claimed is False: appointment_id must be None or absent (populated string or invalid type is a contract violation)
                        if raw_appt_id is not None:
                            if type(raw_appt_id) is not str or raw_appt_id.strip() != "":
                                raise ValueError(
                                    f"RPC claim response claimed=False cannot have populated appointment_id, got: {raw_appt_id!r}"
                                )
                        appointment_id = None

                    assigned_role = payload.get("assigned_role")
                elif isinstance(payload, dict) and "id" in payload:
                    # Legacy Migration 029 flat format:
                    user_data = payload
                    claimed = False
                    appointment_id = None
                    assigned_role = None
                else:
                    raise ValueError(f"Malformed appointment claim payload structure: {payload}")

                # Validate user ID strictly before returning (applies to both 031 envelope and 029 flat format)
                if not isinstance(user_data, dict) or "id" not in user_data:
                    raise ValueError(f"RPC claim response user record missing 'id': {user_data}")

                raw_id = user_data["id"]
                if raw_id is None:
                    raise ValueError(f"RPC claim response user record has null 'id': {user_data}")

                str_id = str(raw_id).strip()
                if not str_id or str_id.lower() == "none":
                    raise ValueError(f"RPC claim response user record contains invalid 'id': {raw_id!r}")

                user_data["id"] = str_id
                return AppointmentClaimResult(
                    user=user_data,
                    claimed=claimed,
                    appointment_id=appointment_id,
                    assigned_role=assigned_role,
                )
        except Exception as exc:
            if _is_account_conflict_exception(exc):
                logger.warning("Account conflict detected in claim RPC for email=%s, uid=%s", email, firebase_uid)
                raise AccountConflictError(f"Account conflict: Email {email} is registered under a different UID.") from exc

            logger.error("claim_pending_admin_appointment RPC execution failed: %s", exc)
            raise
