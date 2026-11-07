"""
Admin Transactional Outbox endpoints.

Provides endpoints for monitoring and manually triggering the transactional outbox worker.
"""

import logging
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.services.outbox_service import OutboxService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/outbox", tags=["Admin Outbox"])


@router.post(
    "/process",
    summary="Process pending outbox tasks (admin)",
    description="Admin only. Triggers immediate batch processing of queued storage outbox tasks.",
)
async def process_outbox(
    batch_size: Annotated[int, Query(ge=1, le=100, description="Number of jobs to process")] = 10,
    lease_seconds: Annotated[int, Query(ge=10, le=300, description="Lease duration in seconds")] = 60,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Process pending outbox jobs."""
    service = OutboxService(db)
    stats = service.process_batch(batch_size=batch_size, lease_seconds=lease_seconds)
    return {
        "status": "success",
        "processed": stats,
    }


@router.get(
    "/status",
    summary="Get outbox queue status (admin)",
    description="Admin only. Returns queue counts grouped by status and recent failed tasks.",
)
async def get_outbox_status(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get queue summary."""
    count_stmt = text(
        """
        SELECT status, COUNT(*)::int AS count
        FROM storage_outbox
        GROUP BY status
        """
    )
    counts = {r["status"]: r["count"] for r in [dict(row._mapping) for row in db.execute(count_stmt).fetchall()]}

    recent_failed_stmt = text(
        """
        SELECT id, bucket_name, object_path, operation, status, attempt_count, last_error, updated_at
        FROM storage_outbox
        WHERE status IN ('FAILED', 'DEAD_LETTER')
        ORDER BY updated_at DESC
        LIMIT 10
        """
    )
    recent_failed = [
        {
            "id": str(r["id"]),
            "bucket_name": r["bucket_name"],
            "object_path": r["object_path"],
            "operation": r["operation"],
            "status": r["status"],
            "attempt_count": r["attempt_count"],
            "last_error": r["last_error"],
            "updated_at": r["updated_at"].isoformat() if r.get("updated_at") else None,
        }
        for r in [dict(row._mapping) for row in db.execute(recent_failed_stmt).fetchall()]
    ]

    return {
        "status_counts": counts,
        "recent_failed": recent_failed,
    }