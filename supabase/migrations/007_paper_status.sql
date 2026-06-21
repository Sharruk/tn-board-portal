-- =============================================================================
-- Migration 007 — Paper Status System
-- TN State Board Learning Platform
-- =============================================================================
-- Adds a status column (draft | published | archived) to papers.
-- Migrates existing data from is_visible boolean.
-- Updates search_papers and increment_download_count RPCs to filter by status.
-- Updates get_admin_stats to count published papers.
-- =============================================================================


-- ── 1. Add status column ──────────────────────────────────────────────────────
ALTER TABLE papers
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'draft'
  CHECK (status IN ('draft', 'published', 'archived'));


-- ── 2. Migrate existing data from is_visible ──────────────────────────────────
UPDATE papers SET status = 'published' WHERE is_visible = true  AND status = 'draft';
UPDATE papers SET status = 'archived'  WHERE is_visible = false AND status = 'draft';


-- ── 3. Update search_papers RPC ───────────────────────────────────────────────
-- Now filters by status = 'published' instead of is_visible = true.
-- Adds status column to return type so callers can inspect it.

CREATE OR REPLACE FUNCTION search_papers(
    q            TEXT,
    p_class_id   INTEGER DEFAULT NULL,
    p_exam_type  TEXT    DEFAULT NULL,
    p_paper_type TEXT    DEFAULT NULL
)
RETURNS TABLE (
    id             INTEGER,
    subject_id     INTEGER,
    exam_type      TEXT,
    year           INTEGER,
    title          TEXT,
    paper_type     TEXT,
    file_path      TEXT,
    public_url     TEXT,
    youtube_url    TEXT,
    is_visible     BOOLEAN,
    status         TEXT,
    download_count INTEGER,
    created_at     TIMESTAMPTZ,
    subject_name   TEXT,
    class_id       INTEGER,
    class_name     TEXT
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
        p.title::TEXT,
        p.paper_type::TEXT,
        p.file_path::TEXT,
        p.public_url::TEXT,
        p.youtube_url::TEXT,
        p.is_visible,
        p.status::TEXT,
        p.download_count,
        p.created_at,
        s.name::TEXT   AS subject_name,
        c.id           AS class_id,
        c.name::TEXT   AS class_name
    FROM   papers   p
    JOIN   subjects s ON s.id = p.subject_id
    JOIN   classes  c ON c.id = s.class_id
    WHERE  p.status = 'published'
      AND (
            p.title     ILIKE '%' || q || '%'
         OR p.exam_type ILIKE '%' || q || '%'
         OR s.name      ILIKE '%' || q || '%'
         OR c.name      ILIKE '%' || q || '%'
      )
      AND (p_class_id   IS NULL OR c.id         = p_class_id)
      AND (p_exam_type  IS NULL OR p.exam_type  = p_exam_type)
      AND (p_paper_type IS NULL OR p.paper_type = p_paper_type)
    ORDER BY p.created_at DESC
    LIMIT 50;
END;
$$;

COMMENT ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) IS
'Searches published papers across title, exam_type, subject name, and class name using ILIKE. '
'Updated in migration 007 to filter by status = published instead of is_visible.';

GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO authenticated;


-- ── 4. Update increment_download_count RPC ────────────────────────────────────
-- Guards on status = 'published' instead of is_visible = true.

CREATE OR REPLACE FUNCTION increment_download_count(paper_id_param INTEGER)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE papers
    SET    download_count = download_count + 1
    WHERE  id     = paper_id_param
      AND  status = 'published';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Paper not found or not published (id=%)', paper_id_param;
    END IF;
END;
$$;

COMMENT ON FUNCTION increment_download_count(INTEGER) IS
'Atomically increments download_count for a published paper. '
'Updated in migration 007 to check status = published.';

GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO authenticated;


-- ── 5. Update get_admin_stats RPC ─────────────────────────────────────────────
-- published_papers replaces the old visible_papers count.

CREATE OR REPLACE FUNCTION get_admin_stats()
RETURNS TABLE (
    total_papers     BIGINT,
    total_downloads  BIGINT,
    total_subjects   BIGINT,
    total_classes    BIGINT,
    visible_papers   BIGINT,
    question_papers  BIGINT,
    answer_keys      BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*)                    FROM papers)                                    AS total_papers,
        (SELECT COALESCE(SUM(download_count), 0) FROM papers)                              AS total_downloads,
        (SELECT COUNT(*)                    FROM subjects)                                  AS total_subjects,
        (SELECT COUNT(*)                    FROM classes)                                   AS total_classes,
        (SELECT COUNT(*)                    FROM papers WHERE status = 'published')         AS visible_papers,
        (SELECT COUNT(*)                    FROM papers WHERE paper_type = 'question')      AS question_papers,
        (SELECT COUNT(*)                    FROM papers WHERE paper_type = 'answer_key')    AS answer_keys;
END;
$$;

COMMENT ON FUNCTION get_admin_stats() IS
'Returns platform-wide statistics for the admin dashboard in one round-trip. '
'Updated in migration 007: visible_papers now counts status = published.';

GRANT EXECUTE ON FUNCTION get_admin_stats() TO authenticated;
