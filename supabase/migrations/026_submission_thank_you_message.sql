-- =============================================================================
-- Migration 026 — Submission Thank-You Message & Contributor Experience
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   1. Add `thank_you_message` TEXT column to `submissions` table.
--      Stores the contributor-facing acknowledgment message shown when an admin
--      approves and publishes their submission.
--
-- Backward Compatible: YES
--   • `thank_you_message` is nullable.
--   • Existing approved rows remain valid.
-- =============================================================================

ALTER TABLE submissions
    ADD COLUMN IF NOT EXISTS thank_you_message TEXT;

COMMENT ON COLUMN submissions.thank_you_message IS
    'Contributor-facing acknowledgment/thank-you message displayed upon approval.';
