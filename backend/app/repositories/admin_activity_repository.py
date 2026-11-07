"""
Admin Activity repository — PostgreSQL data access for Central Admin Activity Logs.
"""

from datetime import datetime
import json
import logging
from typing import Any, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AdminActivityRepository:
    """
    Data access layer for public.admin_activity_logs.

    Architectural Invariant:
    The write method `log_activity()` MUST participate strictly in the caller's
    active SQLAlchemy session (`self._db`). It leaves transaction ownership (commit / rollback)
    entirely to the calling service, guaranteeing atomic consistency between the business
    mutation and the audit trail.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def log_activity(
        self,
        *,
        actor_uid: str,
        actor_email: str,
        actor_name: str,
        actor_role: str,
        action: str,
        target_type: str,
        target_id: str,
        target_title: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Record an administrative action atomically within the caller's active transaction.

        CRITICAL: This method intentionally DOES NOT call `self._db.commit()` or
        `self._db.rollback()`. It enlists the insert into the existing transaction so
        that both the business operation and the audit record commit or rollback together.
        Any database exception will propagate to the caller without being swallowed.
        """
        # Validate non-empty required fields according to NOT NULL constraints
        if not actor_uid or not actor_uid.strip():
            raise ValueError("actor_uid is required for admin activity logging.")
        if not actor_email or not actor_email.strip():
            raise ValueError("actor_email is required for admin activity logging.")
        if not actor_name or not actor_name.strip():
            raise ValueError("actor_name is required for admin activity logging.")
        if not actor_role or not actor_role.strip():
            raise ValueError("actor_role is required for admin activity logging.")
        if not action or not action.strip():
            raise ValueError("action is required for admin activity logging.")
        if not target_type or not target_type.strip():
            raise ValueError("target_type is required for admin activity logging.")
        if not target_id or not str(target_id).strip():
            raise ValueError("target_id is required for admin activity logging.")

        meta_json = json.dumps(metadata or {})

        stmt = text(
            """
            INSERT INTO admin_activity_logs (
                actor_uid, actor_email, actor_name, actor_role, action,
                target_type, target_id, target_title, reason, metadata,
                ip_address, created_at
            )
            VALUES (
                :actor_uid, :actor_email, :actor_name, :actor_role, :action,
                :target_type, :target_id, :target_title, :reason, CAST(:metadata AS jsonb),
                :ip_address, NOW()
            )
            RETURNING id, actor_uid, actor_email, actor_name, actor_role, action,
                      target_type, target_id, target_title, reason, metadata,
                      ip_address, created_at
            """
        )

        res = self._db.execute(
            stmt,
            {
                "actor_uid": actor_uid.strip(),
                "actor_email": actor_email.strip().lower(),
                "actor_name": actor_name.strip(),
                "actor_role": actor_role.strip(),
                "action": action.strip(),
                "target_type": target_type.strip(),
                "target_id": str(target_id).strip(),
                "target_title": target_title.strip() if target_title else None,
                "reason": reason.strip() if reason else None,
                "metadata": meta_json,
                "ip_address": ip_address.strip() if ip_address else None,
            },
        )

        row = res.fetchone()
        if not row:
            raise RuntimeError("Failed to insert admin activity log record.")

        d = dict(row._mapping)
        d["id"] = str(d["id"])
        if isinstance(d.get("metadata"), str):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except Exception:
                d["metadata"] = {}
        return d

    def get_activity_logs(
        self,
        *,
        actor_uid: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[dict[str, Any]], int]:
        """
        Query activity logs with parameterized filtering and deterministic ordering.

        Default ordering: Newest first (`created_at DESC`), with `id DESC` as a stable
        secondary tie-breaker.
        """
        conditions = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if actor_uid and actor_uid.strip():
            conditions.append("actor_uid = :actor_uid")
            params["actor_uid"] = actor_uid.strip()

        if action and action.strip():
            conditions.append("action = :action")
            params["action"] = action.strip()

        if start_date is not None:
            conditions.append("created_at >= :start_date")
            params["start_date"] = start_date

        if end_date is not None:
            conditions.append("created_at <= :end_date")
            params["end_date"] = end_date

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Total count query
        count_stmt = text(f"SELECT COUNT(*) FROM admin_activity_logs {where_clause}")
        # Note: Exclude limit and offset from count params
        count_params = {k: v for k, v in params.items() if k not in ("limit", "offset")}
        total = self._db.execute(count_stmt, count_params).scalar() or 0

        # Data query with deterministic ordering
        data_stmt = text(
            f"""
            SELECT id, actor_uid, actor_email, actor_name, actor_role, action,
                   target_type, target_id, target_title, reason, metadata,
                   ip_address, created_at
            FROM admin_activity_logs
            {where_clause}
            ORDER BY created_at DESC, id DESC
            LIMIT :limit OFFSET :offset
            """
        )

        rows = self._db.execute(data_stmt, params).fetchall()
        result = []
        for r in rows:
            d = dict(r._mapping)
            d["id"] = str(d["id"])
            if isinstance(d.get("metadata"), str):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    d["metadata"] = {}
            result.append(d)

        return result, total