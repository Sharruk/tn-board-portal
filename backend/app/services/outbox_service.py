"""
Transactional Outbox Service — processes queued storage side-effects reliably.

Coordinates worker execution, Supabase Storage API interactions, idempotent
deletion guarantees, and exponential backoff retries.
"""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.db.storage import get_storage_client
from app.repositories.outbox_repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxService:
    """Service layer for outbox queue processing and side-effect coordination."""

    def __init__(self, db: Session, storage: Any = None) -> None:
        self._db = db
        self._repo = OutboxRepository(db)
        if storage is not None:
            self._storage = storage
        else:
            try:
                self._storage = get_storage_client()
            except Exception:
                self._storage = None

    def enqueue_storage_deletion(
        self,
        *,
        bucket_name: str,
        object_path: str,
        payload: Optional[dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Enqueue a durable storage deletion task within the current transaction.
        """
        logger.info(
            "Enqueuing storage deletion: bucket=%s object_path=%s idempotency_key=%s",
            bucket_name,
            object_path,
            idempotency_key,
        )
        return self._repo.enqueue(
            bucket_name=bucket_name,
            object_path=object_path,
            operation="DELETE",
            payload=payload,
            idempotency_key=idempotency_key,
        )

    def process_batch(self, batch_size: int = 10, lease_seconds: int = 60) -> dict[str, int]:
        """
        Claim and execute a batch of pending outbox tasks.

        Each task is isolated so that a failure in one does not block or roll back others.
        """
        jobs = self._repo.claim_jobs(limit=batch_size, lease_seconds=lease_seconds)
        self._db.commit()

        stats = {
            "claimed": len(jobs),
            "completed": 0,
            "failed": 0,
            "dead_letter": 0,
        }

        for job in jobs:
            job_id = job["id"]
            bucket = job["bucket_name"]
            path = job["object_path"]
            operation = job.get("operation", "DELETE")

            logger.info("Processing outbox job %s: %s bucket=%s path=%s", job_id, operation, bucket, path)

            try:
                if operation == "DELETE":
                    self._execute_storage_delete(bucket, path)
                else:
                    logger.warning("Unsupported outbox operation '%s' for job %s", operation, job_id)

                self._repo.mark_completed(job_id)
                self._db.commit()
                stats["completed"] += 1
                logger.info("Outbox job %s marked COMPLETED", job_id)

            except Exception as exc:
                err_msg = str(exc)
                logger.error("Outbox job %s failed: %s", job_id, err_msg, exc_info=True)
                try:
                    res = self._repo.mark_failed(job_id, err_msg)
                    self._db.commit()
                    if res.get("status") == "DEAD_LETTER":
                        stats["dead_letter"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as db_exc:
                    logger.critical("Failed to record failure for job %s: %s", job_id, db_exc)
                    self._db.rollback()

        return stats

    def _execute_storage_delete(self, bucket: str, path: str) -> None:
        """
        Execute storage deletion via Supabase Storage client with idempotency guarantees.
        """
        if not self._storage:
            logger.warning("No storage client available to process deletion for %s/%s", bucket, path)
            return

        try:
            self._storage.from_(bucket).remove([path])
            logger.info("Successfully deleted storage object %s from bucket %s", path, bucket)
        except Exception as exc:
            err_str = str(exc).lower()
            # Idempotent deletion: treat 404 / resource not found as success
            if "not found" in err_str or "404" in err_str or "resource not found" in err_str:
                logger.info("Storage object %s was already missing in bucket %s (treated as success)", path, bucket)
                return
            raise