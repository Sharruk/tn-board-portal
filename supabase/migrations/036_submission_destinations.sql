-- =============================================================================
-- Migration 036: Multi-Category Submission Routing & Contributor Attribution
-- =============================================================================
-- Purpose:
--   1. Allow submissions to be approved into Question Papers, Study Materials,
--      Official Notices, or News & Updates.
--   2. Preserve contributor attribution (contributor_name & submission_id)
--      consistently across all four destination tables.
-- =============================================================================

-- ── 1. Submissions routing tracking ──────────────────────────────────────────
ALTER TABLE submissions
    ADD COLUMN IF NOT EXISTS destination_type TEXT DEFAULT 'paper',
    ADD COLUMN IF NOT EXISTS target_id TEXT;

CREATE INDEX IF NOT EXISTS idx_submissions_destination_type ON submissions (destination_type);

-- ── 2. Study materials attribution ───────────────────────────────────────────
ALTER TABLE study_materials
    ADD COLUMN IF NOT EXISTS submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS contributor_name TEXT;

CREATE INDEX IF NOT EXISTS idx_study_materials_submission_id ON study_materials (submission_id);

-- ── 3. Official notices attribution ──────────────────────────────────────────
ALTER TABLE official_notices
    ADD COLUMN IF NOT EXISTS submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS contributor_name TEXT;

CREATE INDEX IF NOT EXISTS idx_official_notices_submission_id ON official_notices (submission_id);

-- ── 4. News updates attribution ──────────────────────────────────────────────
ALTER TABLE news_updates
    ADD COLUMN IF NOT EXISTS submission_id UUID REFERENCES submissions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS contributor_name TEXT;

CREATE INDEX IF NOT EXISTS idx_news_updates_submission_id ON news_updates (submission_id);
