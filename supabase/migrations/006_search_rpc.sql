-- =============================================================================
-- Migration 006 — Full-Text Search RPC
-- TN State Board Learning Platform
-- =============================================================================
-- Creates a search_papers() function that searches across paper title,
-- exam_type, subject name, and class name in a single query.
--
-- This replaces PostgREST's single-table .or() filter which cannot span
-- joined tables.
--
-- Called from: frontend/src/services/search.js
--   supabase.rpc('search_papers', { q: 'maths', p_class_id: null, ... })
-- =============================================================================

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
        p.download_count,
        p.created_at,
        s.name::TEXT   AS subject_name,
        c.id           AS class_id,
        c.name::TEXT   AS class_name
    FROM   papers   p
    JOIN   subjects s ON s.id = p.subject_id
    JOIN   classes  c ON c.id = s.class_id
    WHERE  p.is_visible = true
      AND (
            p.title     ILIKE '%' || q || '%'
         OR p.exam_type ILIKE '%' || q || '%'
         OR s.name      ILIKE '%' || q || '%'
         OR c.name      ILIKE '%' || q || '%'
      )
      AND (p_class_id   IS NULL OR c.id        = p_class_id)
      AND (p_exam_type  IS NULL OR p.exam_type = p_exam_type)
      AND (p_paper_type IS NULL OR p.paper_type = p_paper_type)
    ORDER BY p.created_at DESC
    LIMIT 50;
END;
$$;

COMMENT ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) IS
'Searches papers across title, exam_type, subject name, and class name using ILIKE. '
'Replaces PostgREST single-table .or() which cannot span joined tables. '
'Called from frontend search.js with alias-expanded terms.';

GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO authenticated;
