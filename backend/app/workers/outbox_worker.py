"""
Transactional Outbox Background Worker.

Polls the `storage_outbox` table using PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`
via `OutboxService.process_batch()` and executes queued Supabase Storage side-effects.

Usage:
    # Continuous daemon (poll every 10 seconds):
    python -m app.workers.outbox_worker

    # Custom polling interval:
    python -m app.workers.outbox_worker --interval 15 --batch-size 20

    # Run once and exit (for cron jobs or testing):
    python -m app.workers.outbox_worker --once
"""

import argparse
import logging
import signal
import sys
import time

from app.db.session import get_sessionmaker
from app.services.outbox_service import OutboxService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | outbox_worker | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("outbox_worker")

# Global graceful shutdown flag
_RUNNING = True


def _signal_handler(signum, frame):
    global _RUNNING
    sig_name = signal.Signals(signum).name
    logger.info("Received signal %s. Initiating graceful shutdown...", sig_name)
    _RUNNING = False


def run_worker(
    poll_interval: float = 10.0,
    batch_size: int = 10,
    lease_seconds: int = 60,
    run_once: bool = False,
) -> None:
    """
    Worker main loop.

    Polls for pending or expired-lease outbox tasks, claims them using
    FOR UPDATE SKIP LOCKED, executes external storage side-effects,
    and updates job status with exponential backoff on failure.
    """
    global _RUNNING

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info(
        "Starting Outbox Worker [interval=%.1fs, batch_size=%d, lease=%ds, once=%s]",
        poll_interval,
        batch_size,
        lease_seconds,
        run_once,
    )

    SessionLocal = get_sessionmaker()

    while _RUNNING:
        try:
            with SessionLocal() as db:
                service = OutboxService(db)
                stats = service.process_batch(
                    batch_size=batch_size,
                    lease_seconds=lease_seconds,
                )

                if stats["claimed"] > 0:
                    logger.info(
                        "Batch processed: claimed=%d, completed=%d, failed=%d, dead_letter=%d",
                        stats["claimed"],
                        stats["completed"],
                        stats["failed"],
                        stats["dead_letter"],
                    )
        except Exception as exc:
            logger.error("Error during outbox batch processing: %s", exc, exc_info=True)

        if run_once:
            logger.info("One-shot run requested. Exiting.")
            break

        # Sleep in small increments for responsive shutdown signal handling
        sleep_elapsed = 0.0
        while _RUNNING and sleep_elapsed < poll_interval:
            time.sleep(min(0.5, poll_interval - sleep_elapsed))
            sleep_elapsed += 0.5

    logger.info("Outbox Worker stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Transactional Outbox Storage Worker")
    parser.add_argument(
        "--interval",
        type=float,
        default=10.0,
        help="Polling interval in seconds between batches (default: 10.0)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Maximum tasks to claim per batch (default: 10)",
    )
    parser.add_argument(
        "--lease-seconds",
        type=int,
        default=60,
        help="Lease duration in seconds before abandoned jobs are reclaimed (default: 60)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process a single batch and exit immediately",
    )

    args = parser.parse_args()
    run_worker(
        poll_interval=args.interval,
        batch_size=args.batch_size,
        lease_seconds=args.lease_seconds,
        run_once=args.once,
    )


if __name__ == "__main__":
    main()