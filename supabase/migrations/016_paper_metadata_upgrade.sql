-- =============================================================================
-- Migration 016 — Paper Metadata Upgrade (Month, District, First Mid Term Test)
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   Upgrade the paper metadata model to accurately represent real Tamil Nadu
--   school examinations. Adds two new nullable columns (month, district),
--   updates the search_papers() RPC to filter/return them, and migrates
--   Class 10 July 2026 papers from 'Model Exam' to 'First Mid Term Test'.
--
-- Backward Compatible: YES
--   • Both new columns are nullable — existing rows are unaffected.
--   • The search_papers() RPC is dropped and recreated. New parameters have
--     DEFAULT NULL so existing callers (without p_month / p_district) still work.
--   • The data migration is scoped to exactly: exam_type='Model Exam', year=2026,
--     Class 10, five specific subjects. No other rows are touched.
--
-- Affects tables: papers
-- Affects RLS: NO
-- Affects RPCs: YES (search_papers)
-- Created: 2026-08-01
-- =============================================================================


-- ============================================================
-- 1. Add month column
-- ============================================================
-- Stores the month name when known (e.g. 'July', 'August').
-- Nullable: not all exam types map to a single month.

ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS month TEXT;

ALTER TABLE papers
    DROP CONSTRAINT IF EXISTS chk_papers_month;

ALTER TABLE papers
    ADD CONSTRAINT chk_papers_month CHECK (
        month IS NULL OR month IN (
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        )
    );

CREATE INDEX IF NOT EXISTS idx_papers_month ON papers (month);

COMMENT ON COLUMN papers.month IS
    'Month the exam was held (e.g. ''July'', ''November''). Nullable — set at upload '
    'time when known. Added in migration 016.';


-- ============================================================
-- 2. Add district column
-- ============================================================
-- Stores the district where the exam was conducted (e.g. 'Chennai').
-- Nullable: many papers are state-wide and have no district.

ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS district TEXT;

CREATE INDEX IF NOT EXISTS idx_papers_district ON papers (district);

COMMENT ON COLUMN papers.district IS
    'Tamil Nadu district for the exam (e.g. ''Chennai'', ''Coimbatore''). '
    'Nullable — only set when the paper is district-specific. Added in migration 016.';


-- ============================================================
-- 3. Replace search_papers() RPC
-- ============================================================
-- Must DROP before CREATE because the RETURNS TABLE definition changes.
-- PostgreSQL does not allow CREATE OR REPLACE when the OUT parameter list changes.
--
-- New parameters added (both DEFAULT NULL for backward compatibility):
--   p_month    TEXT  — filter by exact month name
--   p_district TEXT  — filter by district (ILIKE, partial match)
--
-- New columns added to RETURNS TABLE:
--   month      TEXT
--   district   TEXT
--
-- ILIKE body extended to cover month and district fields.

DROP FUNCTION IF EXISTS search_papers(TEXT, INTEGER, TEXT, TEXT);

CREATE FUNCTION search_papers(
    q             TEXT,
    p_class_id    INTEGER DEFAULT NULL,
    p_exam_type   TEXT    DEFAULT NULL,
    p_paper_type  TEXT    DEFAULT NULL,
    p_month       TEXT    DEFAULT NULL,
    p_district    TEXT    DEFAULT NULL
)
RETURNS TABLE (
    id                INTEGER,
    subject_id        INTEGER,
    exam_type         TEXT,
    year              INTEGER,
    month             TEXT,
    district          TEXT,
    title             TEXT,
    paper_type        TEXT,
    file_path         TEXT,
    public_url        TEXT,
    youtube_url       TEXT,
    is_visible        BOOLEAN,
    status            TEXT,
    download_count    INTEGER,
    created_at        TIMESTAMPTZ,
    subject_name      TEXT,
    class_id          INTEGER,
    class_name        TEXT,
    original_filename TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.subject_id,
        p.exam_type::TEXT,
        p.year,
        p.month::TEXT,
        p.district::TEXT,
        p.title::TEXT,
        p.paper_type::TEXT,
        p.file_path::TEXT,
        p.public_url::TEXT,
        p.youtube_url::TEXT,
        p.is_visible,
        p.status::TEXT,
        p.download_count,
        p.created_at,
        s.name::TEXT            AS subject_name,
        c.id                    AS class_id,
        c.name::TEXT            AS class_name,
        p.original_filename::TEXT
    FROM   papers   p
    JOIN   subjects s ON s.id = p.subject_id
    JOIN   classes  c ON c.id = s.class_id
    WHERE  p.status = 'published'
      AND (
            p.title        ILIKE '%' || q || '%'
         OR p.exam_type    ILIKE '%' || q || '%'
         OR p.month        ILIKE '%' || q || '%'
         OR p.district     ILIKE '%' || q || '%'
         OR s.name         ILIKE '%' || q || '%'
         OR c.name         ILIKE '%' || q || '%'
      )
      AND (p_class_id   IS NULL OR c.id          = p_class_id)
      AND (p_exam_type  IS NULL OR p.exam_type   = p_exam_type)
      AND (p_paper_type IS NULL OR p.paper_type  = p_paper_type)
      AND (p_month      IS NULL OR p.month       = p_month)
      AND (p_district   IS NULL OR p.district    ILIKE '%' || p_district || '%')
    ORDER BY p.created_at DESC
    LIMIT 50;
END;
$$;

COMMENT ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT, TEXT, TEXT) IS
'Searches published papers across title, exam_type, month, district, subject name, and '
'class name using ILIKE. Supports optional filters: class, exam type, paper type, month, '
'district. All filter params default to NULL (no filter). Dropped and recreated in '
'migration 016 to extend the RETURNS TABLE with month and district columns.';

GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT, TEXT, TEXT) TO authenticated;


-- ============================================================
-- 4. Data migration — First Mid Term Test
-- ============================================================
-- Background:
--   Before this exam type existed in the UI, the Class 10 July 2026 batch
--   (Tamil, English, Mathematics, Science, Social Science) from Chennai was
--   uploaded using 'Model Exam' as a workaround.
--
-- Scope:
--   ONLY rows matching ALL of:
--     exam_type = 'Model Exam'
--     year      = 2026
--     class     = 'Class 10'
--     subject   IN ('Tamil', 'English', 'Mathematics', 'Science', 'Social Science')
--
-- No other rows are touched. The UPDATE is idempotent (safe to re-run).

UPDATE papers
SET
    exam_type = 'First Mid Term Test',
    month     = 'July',
    district  = 'Chennai'
WHERE
    exam_type = 'Model Exam'
    AND year  = 2026
    AND subject_id IN (
        SELECT s.id
        FROM   subjects s
        JOIN   classes  c ON c.id = s.class_id
        WHERE  c.name = 'Class 10'
          AND  s.name IN ('Tamil', 'English', 'Mathematics', 'Science', 'Social Science')
    );
