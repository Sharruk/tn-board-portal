"""
Admin Activity repository — append-only immutable audit trail data access.
Directly interfaces with PostgreSQL table `admin_activity_logs`.
"""

import json
import logging
from typing import Any, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AdminActivityRepository:
    """Data access layer for admin activity logging."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def log_activity(
        self,
        actor_uid: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_name: Optional[str] = None,
        actor_role: Optional[str] = None,
        action: str = "unknown",
        target_type: str = "general",
        target_id: str = "0",
        target_title: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        auto_commit: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Append an immutable activity log record.
        Accepts canonical parameters and supports keyword aliases (admin_uid, admin_name, etc.)
        to guarantee callers never trigger runtime TypeError crashes.
        """
        final_actor_uid = actor_uid or kwargs.get("admin_uid") or "system"
        final_actor_email = actor_email or kwargs.get("admin_email") or "system@hungrylearner.internal"
        final_actor_name = actor_name or kwargs.get("admin_name") or final_actor_email.split("@")[0]
        final_actor_role = actor_role or kwargs.get("admin_role") or "ADMIN"
        final_target_title = target_title or kwargs.get("target_name")
        final_metadata = metadata or kwargs.get("details") or {}

        stmt = text(
            """
            INSERT INTO admin_activity_logs (
                actor_uid, actor_email, actor_name, actor_role, action,
                target_type, target_id, target_title, reason, metadata, ip_address, created_at
            )
            VALUES (
                :actor_uid, :actor_email, :actor_name, :actor_role, :action,
                :target_type, :target_id, :target_title, :reason, :metadata, :ip_address, NOW()
            )
            RETURNING id, actor_uid, actor_email, actor_name, actor_role, action,
                      target_type, target_id, target_title, reason, metadata, ip_address, created_at
            """
        )
        params = {
            "actor_uid": final_actor_uid,
            "actor_email": final_actor_email,
            "actor_name": final_actor_name,
            "actor_role": final_actor_role,
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "target_title": final_target_title,
            "reason": reason,
            "metadata": json.dumps(final_metadata),
            "ip_address": ip_address,
        }
        try:
            result = self._db.execute(stmt, params)
            if auto_commit:
                self._db.commit()
            row = result.fetchone()
            if not row:
                raise RuntimeError("Failed to insert admin activity log")
            d = dict(row._mapping)
            d["id"] = str(d["id"])
            return d
        except Exception as exc:
            if auto_commit:
                self._db.rollback()
            logger.warning("Failed to write to admin_activity_logs: %s", exc)
            return {}

    def list_activities(
        self,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> tuple[List[dict[str, Any]], int]:
        """Fetch paginated activity log records."""
        where_clauses = ["1=1"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if action:
            where_clauses.append("action = :action")
            params["action"] = action
        if target_type:
            where_clauses.append("target_type = :target_type")
            params["target_type"] = target_type

        where_sql = " AND ".join(where_clauses)
        count_stmt = text(f"SELECT COUNT(*) FROM admin_activity_logs WHERE {where_sql}")
        try:
            total = self._db.execute(count_stmt, params).scalar() or 0
            stmt = text(
                f"""
                SELECT id, actor_uid, actor_email, actor_name, actor_role, action,
                       target_type, target_id, target_title, reason, metadata, ip_address, created_at
                FROM admin_activity_logs
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            )
            rows = self._db.execute(stmt, params).fetchall()
            items = []
            for r in rows:
                d = dict(r._mapping)
                d["id"] = str(d["id"])
                items.append(d)
            return items, total
        except Exception as exc:
            self._db.rollback()
            logger.warning("Failed to read admin_activity_logs: %s", exc)
            return [], 0
