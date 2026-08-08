-- =============================================================================
-- Migration 018 — Material Submissions
-- TN State Board Learning Platform
-- =============================================================================
-- Adds the public material submission workflow:
--   Public users submit files → status = 'pending'
--   Admin reviews → approves (creates paper) or rejects (no paper created)
--
-- New tables:
--   submissions       — one row per submission form
--   submission_files  — one row per uploaded file (FK → submissions)
--
-- RLS:
--   anon  can INSERT submissions + submission_files (public form)
--   anon  cannot SELECT / UPDATE / DELETE (submissions are private)
--   authenticated (admin) can do everything
--
-- Storage bucket:
--   Automatically creates a PRIVATE bucket "submissions"
--   Adds RLS policies for storage to allow admin full access.
--   The backend uses the service role key for uploads (bypasses RLS)
--
-- Safe to re-run: uses IF NOT EXISTS / DROP IF EXISTS guards throughout.
-- Created: 2026-08-08
-- =============================================================================


-- ── 1. submissions ────────────────────────────────────────────────────────────
-- One row per public submission.  status starts as 'pending'.

CREATE TABLE IF NOT EXISTS submissions (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    publisher_name   TEXT         NOT NULL,
    email            TEXT         NOT NULL,
    details          TEXT,                    -- Optional description from submitter
    status           TEXT         NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'approved', 'rejected')),
    rejection_reason TEXT,                    -- Filled in by admin on rejection
    reviewed_at      TIMESTAMPTZ,             -- Timestamp of approve/reject action
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_status     ON submissions (status);
CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_submissions_email       ON submissions (email);

COMMENT ON TABLE  submissions                  IS 'Public material submissions awaiting admin review.';
COMMENT ON COLUMN submissions.publisher_name   IS 'Contributor/publisher name provided by submitter.';
COMMENT ON COLUMN submissions.email            IS 'Contact email — stored for admin reference only.';
COMMENT ON COLUMN submissions.details          IS 'Optional description or notes from the submitter.';
COMMENT ON COLUMN submissions.status           IS 'pending | approved | rejected';
COMMENT ON COLUMN submissions.rejection_reason IS 'Optional admin reason shown only in admin UI.';
COMMENT ON COLUMN submissions.reviewed_at      IS 'Timestamp when admin approved or rejected.';


-- ── 2. submission_files ───────────────────────────────────────────────────────
-- One row per uploaded file attached to a submission.
-- Files live in Supabase Storage under submissions/{submission_id}/{uuid}.{ext}

CREATE TABLE IF NOT EXISTS submission_files (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id     UUID         NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    original_filename TEXT         NOT NULL,  -- Sanitised original name for display
    storage_path      TEXT         NOT NULL,  -- Storage object key (path inside bucket)
    public_url        TEXT,                   -- Public CDN URL (set after upload)
    file_type         TEXT         NOT NULL,  -- 'pdf' | 'doc' | 'docx' | 'jpg' | 'jpeg' | 'png'
    file_size         BIGINT       NOT NULL,  -- Bytes
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submission_files_submission_id ON submission_files (submission_id);

COMMENT ON TABLE  submission_files                   IS 'Files attached to a submission. One row per file.';
COMMENT ON COLUMN submission_files.original_filename IS 'Sanitised original filename for display — not used as storage key.';
COMMENT ON COLUMN submission_files.storage_path      IS 'Supabase Storage object key: submissions/{uuid}/{uuid}.ext';
COMMENT ON COLUMN submission_files.public_url        IS 'Supabase Storage public CDN URL.';
COMMENT ON COLUMN submission_files.file_type         IS 'File extension/type (pdf, doc, docx, jpg, jpeg, png).';
COMMENT ON COLUMN submission_files.file_size         IS 'File size in bytes.';


-- ── 3. Enable RLS ─────────────────────────────────────────────────────────────

ALTER TABLE submissions      ENABLE ROW LEVEL SECURITY;
ALTER TABLE submission_files ENABLE ROW LEVEL SECURITY;


-- ── 4. RLS policies — submissions ─────────────────────────────────────────────

-- Public users (anon) can insert new submissions (submit the form).
-- They cannot read, update, or delete any submission.
DROP POLICY IF EXISTS "submissions_anon_insert" ON submissions;
CREATE POLICY "submissions_anon_insert"
    ON submissions
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Authenticated admins can read all submissions.
DROP POLICY IF EXISTS "submissions_admin_select" ON submissions;
CREATE POLICY "submissions_admin_select"
    ON submissions
    FOR SELECT
    TO authenticated
    USING (true);

-- Authenticated admins can update submissions (approve/reject).
DROP POLICY IF EXISTS "submissions_admin_update" ON submissions;
CREATE POLICY "submissions_admin_update"
    ON submissions
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Authenticated admins can delete submissions.
DROP POLICY IF EXISTS "submissions_admin_delete" ON submissions;
CREATE POLICY "submissions_admin_delete"
    ON submissions
    FOR DELETE
    TO authenticated
    USING (true);


-- ── 5. RLS policies — submission_files ────────────────────────────────────────

-- Public users (anon) can insert file metadata rows.
DROP POLICY IF EXISTS "submission_files_anon_insert" ON submission_files;
CREATE POLICY "submission_files_anon_insert"
    ON submission_files
    FOR INSERT
    TO anon
    WITH CHECK (true);

-- Authenticated admins can read all file metadata.
DROP POLICY IF EXISTS "submission_files_admin_select" ON submission_files;
CREATE POLICY "submission_files_admin_select"
    ON submission_files
    FOR SELECT
    TO authenticated
    USING (true);

-- Authenticated admins can update file metadata rows.
DROP POLICY IF EXISTS "submission_files_admin_update" ON submission_files;
CREATE POLICY "submission_files_admin_update"
    ON submission_files
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Authenticated admins can delete file metadata rows.
DROP POLICY IF EXISTS "submission_files_admin_delete" ON submission_files;
CREATE POLICY "submission_files_admin_delete"
    ON submission_files
    FOR DELETE
    TO authenticated
    USING (true);


-- ── 6. Grants ─────────────────────────────────────────────────────────────────

GRANT INSERT         ON submissions      TO anon;
GRANT ALL            ON submissions      TO authenticated;
GRANT ALL            ON submissions      TO service_role;

GRANT INSERT         ON submission_files TO anon;
GRANT ALL            ON submission_files TO authenticated;
GRANT ALL            ON submission_files TO service_role;


-- ── 7. Storage Bucket & Policies ──────────────────────────────────────────────

-- Create the private submissions bucket if it doesn't exist
INSERT INTO storage.buckets (id, name, public)
VALUES ('submissions', 'submissions', false)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS policies
-- Note: Supabase backend uses service_role key to upload, bypassing RLS.
-- We only need to ensure admins can read/manage if they use the frontend directly, 
-- but our backend will serve signed URLs, so we don't strictly need frontend RLS for read,
-- but we add it for completeness for authenticated admins.

DROP POLICY IF EXISTS "Admin can access submissions bucket" ON storage.objects;

CREATE POLICY "Admin can access submissions bucket"
    ON storage.objects
    FOR ALL
    TO authenticated
    USING (bucket_id = 'submissions')
    WITH CHECK (bucket_id = 'submissions');
