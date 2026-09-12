"""
Admin Governance repository — direct PostgreSQL access for `admin_governance_requests`.
Matches the live Supabase schema established in Migration 028.
"""

import logging
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AdminGovernanceRepository:
    """Data access layer for admin governance requests."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def acquire_initiator_lock(self, initiator_uid: str) -> None:
        """
        Acquire a transaction-level advisory lock on the initiator's UID.
        Prevents concurrent addition race conditions bypassing the monthly quota.
        """
        lock_stmt = text("SELECT pg_advisory_xact_lock(hashtext(:uid))")
        self._db.execute(lock_stmt, {"uid": initiator_uid})

    def create_request(
        self,
        request_type: str,
        target_user_uid: str,
        target_email: str,
        target_name: str,
        initiated_by_uid: str,
        initiated_by_email: str,
        initiated_by_name: str,
        reason: str,
        status: str = "pending",
        second_approver_uid: Optional[str] = None,
        second_approver_email: Optional[str] = None,
        second_approver_name: Optional[str] = None,
        decision_notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new governance request matching live 028 schema."""
        stmt = text(
            """
            INSERT INTO admin_governance_requests (
                request_type, target_user_uid, target_email, target_name,
                initiated_by_uid, initiated_by_email, initiated_by_name,
                reason, status, second_approver_uid, second_approver_email,
                second_approver_name, second_approved_at, decision_notes,
                created_at, updated_at
            )
            VALUES (
                :request_type, :target_user_uid, :target_email, :target_name,
                :initiated_by_uid, :initiated_by_email, :initiated_by_name,
                :reason, :status, :second_approver_uid, :second_approver_email,
                :second_approver_name,
                CASE WHEN :status = 'approved' THEN NOW() ELSE NULL END,
                :decision_notes,
                NOW(), NOW()
            )
            RETURNING id, request_type, target_user_uid, target_email, target_name,
                      initiated_by_uid, initiated_by_email, initiated_by_name, status,
                      second_approver_uid, second_approver_email, second_approver_name,
                      second_approved_at, decision_notes, reason, created_at, updated_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "request_type": request_type,
                "target_user_uid": target_user_uid,
                "target_email": target_email,
                "target_name": target_name,
                "initiated_by_uid": initiated_by_uid,
                "initiated_by_email": initiated_by_email,
                "initiated_by_name": initiated_by_name,
                "reason": reason,
                "status": status.lower(),
                "second_approver_uid": second_approver_uid,
                "second_approver_email": second_approver_email,
                "second_approver_name": second_approver_name,
                "decision_notes": decision_notes,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            raise RuntimeError("Failed to insert admin governance request")
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def get_by_id(self, request_id: str) -> Optional[dict[str, Any]]:
        """Fetch request by UUID ID."""
        stmt = text(
            """
            SELECT id, request_type, target_user_uid, target_email, target_name,
                   initiated_by_uid, initiated_by_email, initiated_by_name, status,
                   second_approver_uid, second_approver_email, second_approver_name,
                   second_approved_at, decision_notes, reason, created_at, updated_at
            FROM admin_governance_requests
            WHERE id = :id::uuid
            """
        )
        try:
            result = self._db.execute(stmt, {"id": request_id})
            row = result.fetchone()
            if not row:
                return None
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d
        except Exception as exc:
            logger.warning("Error fetching governance request %s: %s", request_id, exc)
            self._db.rollback()
            return None

    def get_pending_removal(self, target_user_uid: str) -> Optional[dict[str, Any]]:
        """Fetch active pending removal request for target Admin."""
        stmt = text(
            """
            SELECT id, request_type, target_user_uid, target_email, target_name,
                   initiated_by_uid, initiated_by_email, initiated_by_name, status,
                   second_approver_uid, second_approver_email, second_approver_name,
                   second_approved_at, decision_notes, reason, created_at, updated_at
            FROM admin_governance_requests
            WHERE target_user_uid = :target_user_uid
              AND request_type = 'admin_removal'
              AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        result = self._db.execute(stmt, {"target_user_uid": target_user_uid})
        row = result.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def list_requests(
        self,
        status: Optional[str] = None,
        request_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List governance requests with optional filtering."""
        where_clauses = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if status:
            where_clauses.append("status = :status")
            params["status"] = status.lower()
        if request_type:
            where_clauses.append("request_type = :request_type")
            params["request_type"] = request_type

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_stmt = text(f"SELECT COUNT(*)::int FROM admin_governance_requests {where_sql}")
        total = self._db.execute(count_stmt, params).scalar() or 0

        list_stmt = text(
            f"""
            SELECT id, request_type, target_user_uid, target_email, target_name,
                   initiated_by_uid, initiated_by_email, initiated_by_name, status,
                   second_approver_uid, second_approver_email, second_approver_name,
                   second_approved_at, decision_notes, reason, created_at, updated_at
            FROM admin_governance_requests
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        )
        rows = self._db.execute(list_stmt, params).fetchall()
        items = []
        for r in rows:
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            items.append(d)
        return items, total

    def update_request_status(
        self,
        request_id: str,
        status: str,
        second_approver_uid: str,
        second_approver_email: Optional[str],
        second_approver_name: str,
        decision_notes: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Update request status ('approved' or 'rejected')."""
        stmt = text(
            """
            UPDATE admin_governance_requests
            SET status = :status,
                second_approver_uid = :second_approver_uid,
                second_approver_email = :second_approver_email,
                second_approver_name = :second_approver_name,
                second_approved_at = NOW(),
                decision_notes = :decision_notes,
                updated_at = NOW()
            WHERE id = :id::uuid AND status = 'pending'
            RETURNING id, request_type, target_user_uid, target_email, target_name,
                      initiated_by_uid, initiated_by_email, initiated_by_name, status,
                      second_approver_uid, second_approver_email, second_approver_name,
                      second_approved_at, decision_notes, reason, created_at, updated_at
            """
        )
        result = self._db.execute(
            stmt,
            {
                "id": request_id,
                "status": status.lower(),
                "second_approver_uid": second_approver_uid,
                "second_approver_email": second_approver_email,
                "second_approver_name": second_approver_name,
                "decision_notes": decision_notes,
            },
        )
        self._db.commit()
        row = result.fetchone()
        if not row:
            return None
        d = dict(row._mapping)
        d["id"] = str(d["id"])
        return d

    def count_monthly_additions(self, initiator_uid: str) -> int:
        """Count additions initiated by a user in the current calendar month."""
        stmt = text(
            """
            SELECT COUNT(*)::int
            FROM admin_governance_requests
            WHERE initiated_by_uid = :uid
              AND request_type = 'admin_addition'
              AND created_at >= date_trunc('month', CURRENT_DATE)
            """
        )
        count = self._db.execute(stmt, {"uid": initiator_uid}).scalar() or 0
        return count
