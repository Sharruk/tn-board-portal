"""
Admin Roles repository — PostgreSQL data access for Super Admin & Admin management.
"""

import json
import logging
from typing import Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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
        try:
            res = self._db.execute(
                text(sql),
                {
                    "email": email,
                    "norm_email": normalized_email,
                    "creator_uid": created_by_uid,
                    "creator_email": created_by_email,
                },
            )
            self._db.commit()
            row = res.fetchone()
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d
        except Exception as exc:
            self._db.rollback()
            raise exc

    def revoke_pending_appointment(self, appointment_id: str) -> Optional[dict[str, Any]]:
        """Revoke a pending admin pre-authorization before sign-in."""
        sql = """
            UPDATE pending_admin_appointments
            SET status = 'revoked', updated_at = NOW()
            WHERE id = :id AND status = 'pending'
            RETURNING id, email, normalized_email, created_by_uid, created_by_email, status, created_at
        """
        try:
            res = self._db.execute(text(sql), {"id": appointment_id})
            self._db.commit()
            row = res.fetchone()
            if not row:
                return None
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d
        except Exception as exc:
            self._db.rollback()
            raise exc

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
            res = self._db.execute(text(primary_sql), {"uid": firebase_uid})
            self._db.commit()
            row = res.fetchone()
            if not row:
                return None
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d
        except Exception as exc:
            self._db.rollback()
            # Resilient fallback if previous_role column does not exist yet
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
            self._db.commit()
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
            res = self._db.execute(text(primary_sql), {"uid": firebase_uid})
            self._db.commit()
            row = res.fetchone()
            if not row:
                return None
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d
        except Exception as exc:
            self._db.rollback()
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
            self._db.commit()
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
    ) -> dict[str, Any]:
        """
        Atomically claims any active pending appointment for this verified email.
        Calls the claim_pending_admin_appointment stored procedure if present,
        or performs an atomic transaction with row locking in Python.
        """
        norm_email = email.strip().lower()

        # Attempt RPC call first
        rpc_sql = "SELECT claim_pending_admin_appointment(:uid, :email, :name, :photo)"
        try:
            res = self._db.execute(
                text(rpc_sql),
                {
                    "uid": firebase_uid,
                    "email": email,
                    "name": display_name,
                    "photo": photo_url,
                },
            )
            self._db.commit()
            row = res.fetchone()
            if row and row[0]:
                data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                data["id"] = str(data["id"])
                return data
        except Exception as exc:
            self._db.rollback()
            logger.debug("claim_pending_admin_appointment RPC not available or failed (%s); using direct transaction", exc)

        # Python-level atomic transaction fallback
        # 1. Account takeover check: Does email exist under a different UID?
        conflict_stmt = text("SELECT id, firebase_uid FROM users WHERE LOWER(email) = :email AND firebase_uid <> :uid LIMIT 1")
        conflict_row = self._db.execute(conflict_stmt, {"email": norm_email, "uid": firebase_uid}).fetchone()
        if conflict_row:
            raise ValueError(f"Account conflict: Email {email} is registered under a different UID.")

        # 2. Check and atomically update pending appointment
        appt_stmt = text(
            """
            UPDATE pending_admin_appointments
            SET status = 'claimed', claimed_at = NOW(), claimed_by_uid = :uid, updated_at = NOW()
            WHERE normalized_email = :email AND status = 'pending'
            RETURNING id
            """
        )
        appt_res = None
        try:
            appt_res = self._db.execute(appt_stmt, {"uid": firebase_uid, "email": norm_email}).fetchone()
        except Exception:
            self._db.rollback()

        # 3. Check existing user record
        u_stmt = text("SELECT id, firebase_uid, email, display_name, role, is_active FROM users WHERE firebase_uid = :uid")
        existing_user = self._db.execute(u_stmt, {"uid": firebase_uid}).fetchone()

        if appt_res:
            target_role = "ADMIN"
        elif existing_user and existing_user._mapping.get("role") in ("ADMIN", "SUPER_ADMIN"):
            target_role = existing_user._mapping.get("role")
        elif existing_user:
            target_role = existing_user._mapping.get("role")
        else:
            target_role = "USER"

        # 4. Upsert user
        if not existing_user:
            ins_stmt = text(
                """
                INSERT INTO users (firebase_uid, email, display_name, role, is_active, photo_url, last_active_at)
                VALUES (:uid, :email, :name, :role, true, :photo, NOW())
                RETURNING id, firebase_uid, email, display_name, role, is_active, created_at, photo_url, last_active_at
                """
            )
            u_res = self._db.execute(
                ins_stmt,
                {"uid": firebase_uid, "email": email, "name": display_name, "role": target_role, "photo": photo_url},
            )
            self._db.commit()
            u_row = u_res.fetchone()
        else:
            upd_stmt = text(
                """
                UPDATE users
                SET 
                    email = :email,
                    photo_url = COALESCE(:photo, photo_url),
                    last_active_at = NOW(),
                    role = CASE WHEN :role = 'ADMIN' AND role NOT IN ('ADMIN', 'SUPER_ADMIN') THEN 'ADMIN'::app_role ELSE role END
                WHERE firebase_uid = :uid
                RETURNING id, firebase_uid, email, display_name, role, is_active, created_at, photo_url, last_active_at
                """
            )
            u_res = self._db.execute(
                upd_stmt,
                {"uid": firebase_uid, "email": email, "photo": photo_url, "role": target_role},
            )
            self._db.commit()
            u_row = u_res.fetchone() or existing_user

        d = dict(u_row._mapping)
        d["id"] = str(d["id"])
        return d

