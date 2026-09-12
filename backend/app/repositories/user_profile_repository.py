"""
User Profile repository — direct PostgreSQL access for user accounts, display names, and roles.
"""

import logging
from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UserProfileRepository:
    """Data access layer for user profile management."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_firebase_uid(self, firebase_uid: str) -> dict[str, Any] | None:
        """Fetch user by firebase_uid with fallback for new governance columns."""
        stmt = text(
            """
            SELECT id, firebase_uid, email, display_name, role, is_active, created_at, updated_at,
                   is_verified_teacher, governance_status, admin_added_by_uid, admin_added_at,
                   verified_teacher_by_uid, verified_teacher_at
            FROM users
            WHERE firebase_uid = :uid
            """
        )
        try:
            row = self._db.execute(stmt, {"uid": firebase_uid}).fetchone()
        except Exception:
            self._db.rollback()
            stmt_fb = text(
                """
                SELECT id, firebase_uid, email, display_name, role, is_active, created_at, updated_at
                FROM users
                WHERE firebase_uid = :uid
                """
            )
            row = self._db.execute(stmt_fb, {"uid": firebase_uid}).fetchone()

        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d.setdefault("is_verified_teacher", False)
        d.setdefault("governance_status", "active")
        return d

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        """Fetch user by normalized lowercase email."""
        clean_email = email.strip().lower()
        stmt = text(
            """
            SELECT id, firebase_uid, email, display_name, role, is_active, created_at, updated_at,
                   is_verified_teacher, governance_status, admin_added_by_uid, admin_added_at,
                   verified_teacher_by_uid, verified_teacher_at
            FROM users
            WHERE LOWER(email) = :email
            ORDER BY CASE WHEN firebase_uid NOT LIKE 'pending_%' THEN 0 ELSE 1 END, created_at ASC
            LIMIT 1
            """
        )
        row = self._db.execute(stmt, {"email": clean_email}).fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        d.setdefault("is_verified_teacher", False)
        d.setdefault("governance_status", "active")
        return d

    def upsert_user(
        self,
        firebase_uid: str,
        email: str,
        display_name: Optional[str] = None,
        role: str = "USER",
        admin_added_by_uid: Optional[str] = None,
        auto_commit: bool = True,
    ) -> dict[str, Any]:
        """Insert or update user record."""
        clean_email = email.strip().lower()
        stmt = text(
            """
            INSERT INTO users (
                firebase_uid, email, display_name, role, is_active,
                admin_added_by_uid, admin_added_at, created_at, updated_at
            )
            VALUES (
                :uid, :email, :display_name, :role, true,
                :admin_added_by_uid, CASE WHEN :role = 'ADMIN' THEN NOW() ELSE NULL END, NOW(), NOW()
            )
            ON CONFLICT (firebase_uid) DO UPDATE
            SET email = EXCLUDED.email,
                display_name = COALESCE(EXCLUDED.display_name, users.display_name),
                role = CASE WHEN users.role IN ('ADMIN', 'SUPER_ADMIN') THEN users.role ELSE EXCLUDED.role END,
                updated_at = NOW()
            RETURNING id, firebase_uid, email, display_name, role, is_active, created_at, updated_at,
                      is_verified_teacher, governance_status
            """
        )
        res = self._db.execute(
            stmt,
            {
                "uid": firebase_uid,
                "email": clean_email,
                "display_name": display_name,
                "role": role,
                "admin_added_by_uid": admin_added_by_uid,
            },
        )
        if auto_commit:
            self._db.commit()
        row = res.fetchone()
        if not row:
            raise RuntimeError("Failed to upsert user record")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def claim_pending_invitation(
        self,
        pending_row_id: str,
        real_firebase_uid: str,
        photo_url: Optional[str] = None,
        display_name: Optional[str] = None,
        auto_commit: bool = True,
    ) -> Optional[dict[str, Any]]:
        """
        Safely bind a pre-provisioned 'pending_{email}' record to the real authenticated Firebase UID.
        Preserves pre-provisioned ADMIN role and attribution while preventing duplicate USER row.
        """
        stmt = text(
            """
            UPDATE users
            SET firebase_uid = :real_uid,
                photo_url = COALESCE(:photo_url, photo_url),
                display_name = COALESCE(:display_name, display_name),
                last_active_at = NOW(),
                updated_at = NOW()
            WHERE id = :id::uuid
              AND firebase_uid LIKE 'pending_%'
            RETURNING id, firebase_uid, email, display_name, role, is_active, created_at, updated_at,
                      is_verified_teacher, governance_status, photo_url, last_active_at
            """
        )
        res = self._db.execute(
            stmt,
            {
                "id": pending_row_id,
                "real_uid": real_firebase_uid,
                "photo_url": photo_url,
                "display_name": display_name,
            },
        )
        if auto_commit:
            self._db.commit()
        row = res.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def update_display_name(self, firebase_uid: str, display_name: str) -> dict[str, Any]:
        """Update user's public display/contribution name."""
        stmt = text(
            """
            UPDATE users
            SET display_name = :display_name, updated_at = NOW()
            WHERE firebase_uid = :uid
            RETURNING id, firebase_uid, email, display_name, role, is_active, created_at, updated_at
            """
        )
        result = self._db.execute(stmt, {"uid": firebase_uid, "display_name": display_name})
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError(f"Failed to update display name for user {firebase_uid}")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def promote_to_contributor(self, firebase_uid: str, auto_commit: bool = True) -> bool:
        """
        Promote a USER to CONTRIBUTOR atomically.
        Does NOT alter ADMIN or SUPER_ADMIN roles.
        """
        stmt = text(
            """
            UPDATE users
            SET role = 'CONTRIBUTOR', updated_at = NOW()
            WHERE firebase_uid = :uid AND role = 'USER'
            RETURNING id
            """
        )
        res = self._db.execute(stmt, {"uid": firebase_uid})
        if auto_commit:
            self._db.commit()
        return res.fetchone() is not None

    def update_role(
        self,
        firebase_uid: str,
        new_role: str,
        admin_added_by_uid: str | None = None,
        auto_commit: bool = True,
    ) -> bool:
        """Update user's role and track who promoted them."""
        stmt = text(
            """
            UPDATE users
            SET role = :role,
                admin_added_by_uid = COALESCE(:promoted_by, admin_added_by_uid),
                admin_added_at = CASE WHEN :role = 'ADMIN' THEN NOW() ELSE admin_added_at END,
                updated_at = NOW()
            WHERE firebase_uid = :uid
            RETURNING id
            """
        )
        res = self._db.execute(
            stmt,
            {"uid": firebase_uid, "role": new_role, "promoted_by": admin_added_by_uid},
        )
        if auto_commit:
            self._db.commit()
        return res.fetchone() is not None

    def update_verified_teacher(
        self,
        firebase_uid: str,
        is_verified: bool,
        verified_by_uid: str | None = None,
        auto_commit: bool = True,
    ) -> bool:
        """Grant or revoke Super-Admin-Verified Teacher trust."""
        stmt = text(
            """
            UPDATE users
            SET is_verified_teacher = :is_verified,
                verified_teacher_by_uid = CASE WHEN :is_verified THEN :verified_by ELSE NULL END,
                verified_teacher_at = CASE WHEN :is_verified THEN NOW() ELSE NULL END,
                updated_at = NOW()
            WHERE firebase_uid = :uid
            RETURNING id
            """
        )
        res = self._db.execute(
            stmt,
            {"uid": firebase_uid, "is_verified": is_verified, "verified_by": verified_by_uid},
        )
        if auto_commit:
            self._db.commit()
        return res.fetchone() is not None

    def update_governance_status(
        self,
        firebase_uid: str,
        governance_status: str,
        auto_commit: bool = True,
    ) -> bool:
        """Update user's governance status ('active', 'pending_removal', 'removed', 'suspended')."""
        stmt = text(
            """
            UPDATE users
            SET governance_status = :status, updated_at = NOW()
            WHERE firebase_uid = :uid
            RETURNING id
            """
        )
        res = self._db.execute(stmt, {"uid": firebase_uid, "status": governance_status})
        if auto_commit:
            self._db.commit()
        return res.fetchone() is not None
