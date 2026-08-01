-- =============================================================================
-- Migration 015 — Expired Notices Visibility (Archive Mode)
-- TN State Board Student Portal
-- =============================================================================
-- Purpose: Show expired (archived) notices to students with clear visual
--          distinction instead of hiding them completely from the public portal.
--
-- Context:
--   Migration 008 defined notices_public_select with:
--       USING (is_visible = true AND (expires_at IS NULL OR expires_at > NOW()))
--   Migration 008 defined search_notices() with the expires_at > NOW() filter.
--   Migration 007 updated get_admin_stats() to use status = 'published' for papers.
--
--   This migration:
--     1. Relaxes notices_public_select — removes the expires_at gate.
--     2. Replaces search_notices() — adds is_expired + expires_at to the return type
--        and removes the expires_at WHERE filter.  Because the return type changes,
--        the function must be DROPped before being recreated (PostgreSQL rule).
--     3. Replaces get_admin_stats() — adds notice breakdown columns
--        (active_notices, expired_notices, draft_notices).  Same DROP-then-CREATE
--        pattern required because the return TABLE definition changes.
--
-- Why DROP + CREATE instead of CREATE OR REPLACE?
--   PostgreSQL raises ERROR 42P13 ("cannot change return type of existing function")
--   when CREATE OR REPLACE would alter the OUT parameter list.  The only safe
--   upgrade path is:
--       DROP FUNCTION IF EXISTS <name>(<arg types>);
--       CREATE FUNCTION <name>(<arg types>) RETURNS TABLE (...) ...;
--   DROP FUNCTION IF EXISTS is idempotent — safe to re-run if the function was
--   already replaced.  Grants must be reapplied after every DROP because they are
--   stored on the function OID, which changes on each recreate.
--
-- Backward compatible: YES
--   • All existing columns in both functions are preserved.
--   • New columns are additive.
--   • RLS change only widens access (adds expired visible rows); it does not
--     remove access to any rows that were previously reachable.
--
-- Affects tables:   official_notices (RLS policy only, no schema change)
-- Affects RLS:      YES (updates notices_public_select)
-- Affects RPCs:     YES (replaces search_notices, get_admin_stats)
-- Created: 2026-07-10
-- =============================================================================


-- =============================================================================
-- 1. RLS policy update
-- =============================================================================
-- Drop the old policy that blocked expired notices from public view.
-- The new policy lets anon see all is_visible = true rows regardless of expiry.
-- Expiry distinction is now handled at the frontend presentation layer only.

DROP POLICY IF EXISTS "notices_public_select" ON official_notices;

CREATE POLICY "notices_public_select" ON official_notices
    FOR SELECT
    TO anon, authenticated
    USING (is_visible = true);

COMMENT ON POLICY "notices_public_select" ON official_notices IS
'Public can read all visible notices (active and expired/archived). '
'Expiry distinction is handled at the frontend presentation layer. '
'Updated in migration 015 — previously this policy also filtered expires_at > NOW().';


-- =============================================================================
-- 2. Replace search_notices() with updated return type
-- =============================================================================
-- The original function was created in migration 008 and returned 13 columns.
-- We add is_expired (computed BOOLEAN) and expires_at (TIMESTAMPTZ) — 15 columns total.
-- The WHERE clause no longer filters out expired rows.

-- Step 1: Drop the old function to allow the return-type change.
DROP FUNCTION IF EXISTS search_notices(TEXT, TEXT, INTEGER, INTEGER);

-- Step 2: Recreate with the extended RETURNS TABLE.
CREATE FUNCTION search_notices(
    q             TEXT,
    p_category    TEXT    DEFAULT NULL,
    p_class_id    INTEGER DEFAULT NULL,
    p_year        INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id             INTEGER,
    title          TEXT,
    category       TEXT,
    class_id       INTEGER,
    class_name     TEXT,
    year           INTEGER,
    description    TEXT,
    public_url     TEXT,
    file_type      TEXT,
    is_pinned      BOOLEAN,
    -- New columns added in migration 015:
    is_expired     BOOLEAN,
    expires_at     TIMESTAMPTZ,
    -- Existing counter columns:
    view_count     INTEGER,
    download_count INTEGER,
    created_at     TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.id,
        n.title::TEXT,
        n.category::TEXT,
        n.class_id,
        c.name::TEXT    AS class_name,
        n.year,
        n.description::TEXT,
        n.public_url::TEXT,
        n.file_type::TEXT,
        n.is_pinned,
        -- Computed: true when an expiry date exists and it is in the past
        (n.expires_at IS NOT NULL AND n.expires_at <= NOW()) AS is_expired,
        n.expires_at,
        n.view_count,
        n.download_count,
        n.created_at
    FROM   official_notices n
    LEFT JOIN classes c ON c.id = n.class_id
    WHERE  n.is_visible = true
      AND  (
               n.title       ILIKE '%' || q || '%'
            OR n.category    ILIKE '%' || q || '%'
            OR n.description ILIKE '%' || q || '%'
            OR (c.name IS NOT NULL AND c.name ILIKE '%' || q || '%')
           )
      AND  (p_category IS NULL OR n.category = p_category)
      AND  (p_class_id IS NULL OR n.class_id = p_class_id)
      AND  (p_year     IS NULL OR n.year     = p_year)
    ORDER BY n.is_pinned DESC, n.created_at DESC
    LIMIT 50;
END;
$$;

COMMENT ON FUNCTION search_notices(TEXT, TEXT, INTEGER, INTEGER) IS
'Full-text ILIKE search over official_notices. Filters by category, class, and year. '
'Returns all visible rows including expired (archived) ones — the expires_at WHERE gate '
'was removed in migration 015. is_expired computed column tells the frontend to render '
'archive styling. expires_at column exposed for display. '
'Pinned notices are ranked first within results. '
'Function was dropped and recreated in migration 015 to extend the RETURNS TABLE definition. '
'Called from frontend services/search.js via supabase.rpc().';

-- Step 3: Reapply grants (lost when the function was dropped).
GRANT EXECUTE ON FUNCTION search_notices(TEXT, TEXT, INTEGER, INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION search_notices(TEXT, TEXT, INTEGER, INTEGER) TO authenticated;


-- =============================================================================
-- 3. Replace get_admin_stats() with updated return type
-- =============================================================================
-- Migration 007 last updated this function; its RETURNS TABLE has 7 columns.
-- We add 3 notice-breakdown columns — 10 columns total.
-- The paper-related query logic preserves the migration 007 wording exactly
-- (status = 'published' for visible_papers, not is_visible = true).

-- Step 1: Drop the old function to allow the return-type change.
DROP FUNCTION IF EXISTS get_admin_stats();

-- Step 2: Recreate with the extended RETURNS TABLE.
CREATE FUNCTION get_admin_stats()
RETURNS TABLE (
    -- Existing columns (unchanged from migration 007)
    total_papers     BIGINT,
    total_downloads  BIGINT,
    total_subjects   BIGINT,
    total_classes    BIGINT,
    visible_papers   BIGINT,
    question_papers  BIGINT,
    answer_keys      BIGINT,
    -- New columns added in migration 015
    active_notices   BIGINT,
    expired_notices  BIGINT,
    draft_notices    BIGINT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        -- Papers stats — logic preserved exactly from migration 007
        (SELECT COUNT(*)                         FROM papers)                                          AS total_papers,
        (SELECT COALESCE(SUM(download_count), 0) FROM papers)                                         AS total_downloads,
        (SELECT COUNT(*)                         FROM subjects)                                        AS total_subjects,
        (SELECT COUNT(*)                         FROM classes)                                         AS total_classes,
        (SELECT COUNT(*)                         FROM papers WHERE status = 'published')               AS visible_papers,
        (SELECT COUNT(*)                         FROM papers WHERE paper_type = 'question')            AS question_papers,
        (SELECT COUNT(*)                         FROM papers WHERE paper_type = 'answer_key')          AS answer_keys,
        -- Notice stats — new in migration 015
        -- active: visible + not yet expired (no expires_at, or future expiry)
        (SELECT COUNT(*) FROM official_notices
            WHERE is_visible = true
              AND (expires_at IS NULL OR expires_at > NOW()))                                          AS active_notices,
        -- expired/archived: visible + has a past expiry date
        (SELECT COUNT(*) FROM official_notices
            WHERE is_visible = true
              AND expires_at IS NOT NULL
              AND expires_at <= NOW())                                                                  AS expired_notices,
        -- draft: not yet made visible (is_visible = false)
        (SELECT COUNT(*) FROM official_notices
            WHERE is_visible = false)                                                                   AS draft_notices;
END;
$$;

COMMENT ON FUNCTION get_admin_stats() IS
'Returns platform-wide statistics for the admin dashboard in one round-trip. '
'Updated in migration 007: visible_papers counts status = published. '
'Extended in migration 015: adds active_notices, expired_notices, draft_notices. '
'Function was dropped and recreated in migration 015 to extend the RETURNS TABLE definition.';

-- Step 3: Reapply grants (lost when the function was dropped).
-- get_admin_stats is admin-only; anon does not need it.
GRANT EXECUTE ON FUNCTION get_admin_stats() TO authenticated;


-- =============================================================================
-- 4. Indexes
-- =============================================================================
-- idx_notices_expires_at already exists from migration 008 — no action needed.
-- No new schema columns were added — no new indexes required.
