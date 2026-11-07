-- =============================================================================
-- Migration 032 — Transactional Outbox for Supabase Storage Operations
-- TN State Board Learning Platform
-- =============================================================================
-- Problem:
--   PostgreSQL transactions cannot atomically encompass external HTTP calls to
--   Supabase Storage. If a storage deletion happens synchronously before a database
--   commit that rolls back, files are destroyed with no way to recover them. If a
--   storage deletion happens after commit and fails due to network partitions,
--   orphaned storage files remain indefinitely with zero visibility or retry.
--
-- Solution:
--   Transactional Outbox Pattern.
--   When entities (papers, official notices, news updates) are deleted or updated,
--   an outbox task is recorded within the EXACT SAME PostgreSQL transaction.
--   A resilient worker polls the outbox using SELECT ... FOR UPDATE SKIP LOCKED,
--   executes the Storage API removal, and records completion or exponential-backoff retries.
--
-- Guarantees:
--   1. Atomic creation: Database row mutation + admin activity audit log + outbox task
--      are committed or rolled back together.
--   2. At-least-once delivery: Tasks are retried with exponential backoff if Storage fails.
--   3. Idempotent deletion: Storage 404 / 'not found' is treated as success.
--   4. Crash resilience: Stuck 'PROCESSING' tasks whose lease expired are automatically
--      reclaimed.
-- =============================================================================

CREATE TABLE IF NOT EXISTS storage_outbox (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket_name     VARCHAR(64)     NOT NULL,
    object_path     TEXT            NOT NULL,
    operation       VARCHAR(32)     NOT NULL DEFAULT 'DELETE',
    payload         JSONB           NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(20)     NOT NULL DEFAULT 'PENDING'
                                    CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'DEAD_LETTER')),
    attempt_count   INTEGER         NOT NULL DEFAULT 0,
    max_attempts    INTEGER         NOT NULL DEFAULT 5,
    next_retry_at   TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    leased_at       TIMESTAMPTZ,
    last_error      TEXT,
    idempotency_key VARCHAR(255)    UNIQUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- Partial index for high-performance worker polling
CREATE INDEX IF NOT EXISTS idx_storage_outbox_poll
ON storage_outbox (status, next_retry_at, created_at)
WHERE status IN ('PENDING', 'FAILED');

-- Partial index for detecting abandoned / timed-out leases
CREATE INDEX IF NOT EXISTS idx_storage_outbox_stuck
ON storage_outbox (status, leased_at)
WHERE status = 'PROCESSING';

COMMENT ON TABLE storage_outbox IS
  'Transactional outbox for durable asynchronous Supabase Storage side-effects.';
COMMENT ON COLUMN storage_outbox.status IS
  'PENDING: queued; PROCESSING: leased by worker; COMPLETED: done; FAILED: retrying; DEAD_LETTER: exhausted retries.';
COMMENT ON COLUMN storage_outbox.leased_at IS
  'Timestamp when worker acquired the lease; used for crash recovery timeout.';
COMMENT ON COLUMN storage_outbox.idempotency_key IS
  'Deterministic key to prevent duplicate enqueueing within or across transactions.';

-- RLS: Only backend service role and authenticated admins have access
ALTER TABLE storage_outbox ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admins can view storage outbox" ON storage_outbox;
CREATE POLICY "Admins can view storage outbox"
    ON storage_outbox
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.firebase_uid = auth.uid()
              AND users.role IN ('ADMIN', 'SUPER_ADMIN')
              AND users.is_active = true
        )
    );

GRANT SELECT, INSERT, UPDATE, DELETE ON storage_outbox TO service_role;