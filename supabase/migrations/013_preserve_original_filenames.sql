-- =============================================================================
-- Migration 013 — Preserve Original Uploaded Filenames
-- TN State Board Learning Platform
-- =============================================================================
-- Problem:
--   Uploaded PDFs are stored in Supabase Storage using a UUID-based filename
--   (e.g. 4b750e1e-c692-4c8c-b5bb-a7b8db31ed43.pdf).  When users download a
--   paper the browser receives the UUID name, which is confusing and
--   unprofessional.
--
-- Solution:
--   Add an `original_filename` TEXT column to the `papers` table.
--   The application layer populates this field with the original file's name
--   (e.g. Class10_Science_MonthlyTest_June2026_Chennai_QP.pdf) at upload time.
--   The download utility then uses this value to set the Content-Disposition
--   filename shown to the user.
--
-- Backward Compatibility:
--   • The column is nullable — existing rows are unaffected (original_filename
--     will be NULL for all pre-migration papers).
--   • The frontend download utility falls back gracefully:
--       original_filename  →  paper.title + ".pdf"  →  "download.pdf"
--   • No existing data is modified.
-- =============================================================================

ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS original_filename TEXT;

COMMENT ON COLUMN papers.original_filename IS
    'The original filename of the uploaded PDF as provided by the user '
    '(e.g. Class10_Maths_Annual_2024.pdf). NULL for papers uploaded before '
    'this migration. The download utility falls back to paper.title + ".pdf" '
    'when this column is NULL.';
