-- =============================================================================
-- Migration 020 — Add Firebase UID to Submissions
-- TN State Board Learning Platform
-- =============================================================================

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS firebase_uid TEXT;

CREATE INDEX IF NOT EXISTS idx_submissions_firebase_uid ON submissions (firebase_uid);

COMMENT ON COLUMN submissions.firebase_uid IS 'Firebase UID of the user who submitted the material.';
