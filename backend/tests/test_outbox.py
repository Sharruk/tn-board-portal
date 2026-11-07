"""
Tests for Transactional Outbox repository, service, and admin endpoints:
  - Enqueue task within transaction without early commit
  - Claim jobs with FOR UPDATE SKIP LOCKED
  - Process batch with mock Supabase Storage
  - Idempotent storage deletion (404 / resource not found handled as success)
  - Exponential backoff and dead-letter state transitions
  - POST /api/v1/admin/outbox/process
  - GET  /api/v1/admin/outbox/status
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import require_admin
from app.dependencies.supabase import get_db
from app.main import app
from app.repositories.outbox_repository import OutboxRepository
from app.services.outbox_service import OutboxService


class MockRow:
    def __init__(self, data: dict):
        self._mapping = data

    def __getitem__(self, key):
        return self._mapping[key]

    def get(self, key, default=None):
        return self._mapping.get(key, default)


class MockResult:
    def __init__(self, rows: list[dict] | None = None, scalar_val=None, rowcount=1):
        self._rows = [MockRow(r) for r in (rows or [])]
        self._scalar = scalar_val
        self.rowcount = rowcount

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._scalar


_NOW = datetime.now(timezone.utc)

SAMPLE_OUTBOX_JOB = {
    "id": "job-1111-2222",
    "bucket_name": "papers",
    "object_path": "uuid-123.pdf",
    "operation": "DELETE",
    "payload": {"paper_id": 42},
    "status": "PENDING",
    "attempt_count": 0,
    "max_attempts": 5,
    "next_retry_at": _NOW,
    "leased_at": None,
    "last_error": None,
    "idempotency_key": "delete:papers:42:uuid-123.pdf",
    "created_at": _NOW,
    "updated_at": _NOW,
    "completed_at": None,
}


def test_outbox_enqueue_does_not_commit():
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([SAMPLE_OUTBOX_JOB])

    repo = OutboxRepository(mock_db)
    result = repo.enqueue(
        bucket_name="papers",
        object_path="uuid-123.pdf",
        operation="DELETE",
        idempotency_key="delete:papers:42:uuid-123.pdf",
    )

    assert result["id"] == "job-1111-2222"
    assert result["bucket_name"] == "papers"
    # CRITICAL: enqueue must NOT commit — transaction belongs to calling service
    assert not mock_db.commit.called


def test_outbox_claim_jobs():
    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([SAMPLE_OUTBOX_JOB])

    repo = OutboxRepository(mock_db)
    jobs = repo.claim_jobs(limit=10, lease_seconds=60)

    assert len(jobs) == 1
    assert jobs[0]["status"] == "PENDING"
    assert "for update skip locked" in str(mock_db.execute.call_args[0][0]).lower()


def test_outbox_service_process_batch_success():
    mock_db = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_storage.from_.return_value = mock_bucket

    mock_db.execute.return_value = MockResult([SAMPLE_OUTBOX_JOB])

    service = OutboxService(db=mock_db, storage=mock_storage)
    stats = service.process_batch(batch_size=10, lease_seconds=60)

    assert stats["claimed"] == 1
    assert stats["completed"] == 1
    assert stats["failed"] == 0
    mock_bucket.remove.assert_called_once_with(["uuid-123.pdf"])


def test_outbox_service_idempotent_404_treated_as_success():
    mock_db = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_storage.from_.return_value = mock_bucket

    # Simulate 404 from Supabase Storage client
    mock_bucket.remove.side_effect = Exception("Storage resource not found (404)")

    mock_db.execute.return_value = MockResult([SAMPLE_OUTBOX_JOB])

    service = OutboxService(db=mock_db, storage=mock_storage)
    stats = service.process_batch(batch_size=10, lease_seconds=60)

    # 404 is treated as already deleted, hence marked COMPLETED
    assert stats["completed"] == 1
    assert stats["failed"] == 0


def test_outbox_service_retry_and_dead_letter():
    mock_db = MagicMock()
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_storage.from_.return_value = mock_bucket

    # Simulate network timeout
    mock_bucket.remove.side_effect = RuntimeError("Connection timed out to storage CDN")

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "candidate_jobs" in sql:
            # Return job that already failed 4 times
            return MockResult([{**SAMPLE_OUTBOX_JOB, "attempt_count": 4, "max_attempts": 5}])
        if "attempt_count, max_attempts" in sql:
            return MockResult([{"attempt_count": 4, "max_attempts": 5}])
        if "update storage_outbox" in sql:
            return MockResult([{"status": "DEAD_LETTER", "attempt_count": 5}])
        return MockResult([])

    mock_db.execute.side_effect = execute_handler

    service = OutboxService(db=mock_db, storage=mock_storage)
    stats = service.process_batch(batch_size=10, lease_seconds=60)

    assert stats["claimed"] == 1
    assert stats["completed"] == 0
    assert stats["dead_letter"] == 1


def test_admin_outbox_process_endpoint():
    mock_db = MagicMock()
    mock_storage = MagicMock()
    mock_db.execute.return_value = MockResult([])

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "SUPER_ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.post("/api/v1/admin/outbox/process?batch_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "processed" in data
    finally:
        app.dependency_overrides.clear()


def test_admin_outbox_status_endpoint():
    mock_db = MagicMock()

    def execute_handler(stmt, params=None):
        sql = str(stmt).lower()
        if "group by status" in sql:
            return MockResult([{"status": "PENDING", "count": 2}, {"status": "COMPLETED", "count": 15}])
        if "status in ('failed', 'dead_letter')" in sql:
            return MockResult([])
        return MockResult([])

    mock_db.execute.side_effect = execute_handler

    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[require_admin] = lambda: {
        "user_id": "admin-1",
        "email": "admin@example.com",
        "role": "ADMIN",
    }

    try:
        client = TestClient(app)
        resp = client.get("/api/v1/admin/outbox/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status_counts"]["PENDING"] == 2
        assert data["status_counts"]["COMPLETED"] == 15
    finally:
        app.dependency_overrides.clear()


def test_outbox_worker_run_once(monkeypatch):
    from app.workers.outbox_worker import run_worker

    mock_db = MagicMock()
    mock_db.execute.return_value = MockResult([])

    class MockContextSession:
        def __enter__(self):
            return mock_db
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("app.workers.outbox_worker.get_sessionmaker", lambda: MockContextSession)

    # Run once without blocking
    run_worker(poll_interval=0.1, batch_size=5, lease_seconds=30, run_once=True)