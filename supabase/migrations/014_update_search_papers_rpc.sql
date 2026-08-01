-- =============================================================================
-- Migration 014 — Update search_papers RPC to return original_filename
-- TN State Board Learning Platform
-- =============================================================================
-- Context:
--   Migration 013 added `original_filename` to the `papers` table.
--   The search_papers() RPC must also return this column so that the frontend
--   download utility can use the original filename from search results,
--   not just from the paper detail page.
--
-- Why DROP before CREATE?
--   PostgreSQL does not allow CREATE OR REPLACE FUNCTION when the RETURNS TABLE
--   definition (OUT parameter list) changes — it raises:
--     ERROR 42P13: cannot change return type of existing function
--   The only safe fix is to DROP the old function first, then CREATE the new
--   one.  DROP FUNCTION IF EXISTS is used so the migration is re-runnable and
--   safe if the old function no longer exists.
--
-- Change:
--   • Adds `original_filename TEXT` to the RETURNS TABLE definition.
--   • Adds `p.original_filename::TEXT` to the SELECT list.
--   • All other logic, filters, ORDER BY, LIMIT, and grants are identical
--     to the original function defined in migration 006.
--
-- Backward Compatibility:
--   • Existing papers with original_filename = NULL return NULL from this
--     function — the frontend falls back gracefully to paper.title + ".pdf".
--   • The function name and parameter types are unchanged so no client-side
--     call sites need updating.
-- =============================================================================

-- Step 1: Drop the existing function so we can redefine the RETURNS TABLE.
-- IF EXISTS makes this safe to re-run even if the function was already replaced.
DROP FUNCTION IF EXISTS search_papers(TEXT, INTEGER, TEXT, TEXT);

-- Step 2: Recreate the function with the updated return type.
CREATE FUNCTION search_papers(
    q            TEXT,
    p_class_id   INTEGER DEFAULT NULL,
    p_exam_type  TEXT    DEFAULT NULL,
    p_paper_type TEXT    DEFAULT NULL
)
RETURNS TABLE (
    id                INTEGER,
    subject_id        INTEGER,
    exam_type         TEXT,
    year              INTEGER,
    title             TEXT,
    paper_type        TEXT,
    file_path         TEXT,
    public_url        TEXT,
    youtube_url       TEXT,
    is_visible        BOOLEAN,
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
        p.title::TEXT,
        p.paper_type::TEXT,
        p.file_path::TEXT,
        p.public_url::TEXT,
        p.youtube_url::TEXT,
        p.is_visible,
        p.download_count,
        p.created_at,
        s.name::TEXT            AS subject_name,
        c.id                    AS class_id,
        c.name::TEXT            AS class_name,
        p.original_filename::TEXT
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
      AND (p_class_id   IS NULL OR c.id         = p_class_id)
      AND (p_exam_type  IS NULL OR p.exam_type  = p_exam_type)
      AND (p_paper_type IS NULL OR p.paper_type = p_paper_type)
    ORDER BY p.created_at DESC
    LIMIT 50;
END;
$$;

COMMENT ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) IS
'Searches papers across title, exam_type, subject name, and class name using ILIKE. '
'Returns original_filename (added in migration 013) so the download utility can '
'preserve the original uploaded filename. NULL for papers uploaded before migration 013. '
'Function was dropped and recreated in migration 014 to extend the RETURNS TABLE definition.';

-- Step 3: Reapply permissions (grants are lost when the function is dropped).
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO authenticated;
