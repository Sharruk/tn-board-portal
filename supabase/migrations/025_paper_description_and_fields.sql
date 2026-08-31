-- =============================================================================
-- Migration 025 — Paper Description, Status Resilience, and Submission Linking
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   1. Add `description` TEXT column to `papers` for public paper summaries.
--   2. Ensure `status` TEXT column exists on `papers` (safe forward check).
--   3. Ensure indexes on `status` and `submission_id`.
--   4. Idempotent backfill from `is_visible` for existing rows.
--
-- Backward Compatible: YES
--   • `description` is nullable.
--   • `status` has default 'published' and check constraint.
--   • Existing rows preserve visibility mappings.
-- =============================================================================

-- ── 1. Add description column ────────────────────────────────────────────────
ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS description TEXT;

COMMENT ON COLUMN papers.description IS
    'Optional human-readable description / summary of the paper and exam.';

-- ── 2. Ensure status column exists safely ─────────────────────────────────────
ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'published'
    CHECK (status IN ('draft', 'published', 'archived'));

CREATE INDEX IF NOT EXISTS idx_papers_status ON papers (status);

-- ── 3. Ensure submission_id and contributor_name exist ────────────────────────
ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL;

ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS contributor_name TEXT;

CREATE INDEX IF NOT EXISTS idx_papers_submission_id ON papers (submission_id);

-- ── 4. Migrate/Sync status from is_visible for legacy rows ────────────────────
UPDATE papers
SET status = 'published'
WHERE (status IS NULL OR status = 'draft')
  AND (is_visible IS TRUE OR is_visible IS NULL);

UPDATE papers
SET status = 'archived'
WHERE (status IS NULL OR status = 'draft')
  AND is_visible IS FALSE;
