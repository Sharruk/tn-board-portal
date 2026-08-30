-- =============================================================================
-- Migration 024 — Paper Contributor Link & Submission Reference
-- TN State Board Learning Platform
-- =============================================================================
-- Links published papers back to their origin submission and contributor name.

ALTER TABLE papers ADD COLUMN IF NOT EXISTS submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL;
ALTER TABLE papers ADD COLUMN IF NOT EXISTS contributor_name TEXT;

CREATE INDEX IF NOT EXISTS idx_papers_submission_id ON papers (submission_id);

COMMENT ON COLUMN papers.submission_id IS 'Original material submission UUID if paper came from user contribution.';
COMMENT ON COLUMN papers.contributor_name IS 'Display name of contributor shown publicly.';
