"""
Audit Logging Service
=====================
Records admin actions to the audit_logs table.

Actions logged:
  login_success   — admin logged in
  login_failure   — bad credentials
  login_blocked   — account locked (prevented login)
  upload          — paper uploaded
  bulk_upload     — paper uploaded via bulk upload
  edit            — paper metadata edited
  delete          — paper deleted

Failures in audit logging are caught and swallowed so that
the primary action always succeeds even if logging has a transient error.
"""

import json
import logging
from sqlalchemy.orm import Session
from app.models.models import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    action: str,
    admin_id: int | None = None,
    admin_email: str | None = None,
    target_paper_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Write an audit log entry.
    Silently swallows errors so that the primary request is never affected.
    """
    try:
        entry = AuditLog(
            admin_id=admin_id,
            admin_email=admin_email,
            action=action,
            target_paper_id=target_paper_id,
            target_details=json.dumps(details) if details else None,
            ip_address=ip_address,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        logger.warning("Audit log write failed (action=%s): %s", action, exc)
        try:
            db.rollback()
        except Exception:
            pass
