-- =============================================================================
-- Migration 005 — Search Analytics Indexes and Retention Policy
-- TN State Board Learning Platform
-- =============================================================================
-- The search_queries table and its RLS policies were created in 001 and 003.
-- This migration adds:
--   1. A composite index for the analytics aggregation query (term + count)
--   2. An optional scheduled cleanup function to prevent unbounded growth
--   3. A view for convenient admin queries
-- =============================================================================


-- ── Additional index for aggregation performance ──────────────────────────────
-- The get_search_analytics() function groups by LOWER(TRIM(term)).
-- This functional index speeds up that specific aggregation.

CREATE INDEX IF NOT EXISTS idx_search_queries_normalised_term
    ON search_queries (LOWER(TRIM(term)));


-- ── Admin convenience view ────────────────────────────────────────────────────
-- Shows the top 100 search terms with their frequency.
-- Queryable from Supabase Dashboard or via supabase.from('search_term_counts').select()

CREATE OR REPLACE VIEW search_term_counts AS
SELECT
    LOWER(TRIM(term))  AS term,
    COUNT(*)           AS search_count,
    MAX(searched_at)   AS last_searched_at,
    AVG(result_count)  AS avg_result_count
FROM   search_queries
GROUP  BY LOWER(TRIM(term))
ORDER  BY search_count DESC
LIMIT  100;

COMMENT ON VIEW search_term_counts IS
'Aggregated search term frequency — top 100 terms by search count. '
'Read-only convenience view for the admin dashboard.';


-- ── Retention cleanup function ────────────────────────────────────────────────
-- Deletes search_queries rows older than N days.
-- Call manually or schedule with pg_cron (Supabase Pro) or an external cron job.
--
-- Usage:
--   SELECT prune_old_search_queries(90);  -- delete entries older than 90 days
--
-- On Supabase free tier, run manually from the SQL Editor when the table grows large.

CREATE OR REPLACE FUNCTION prune_old_search_queries(older_than_days INTEGER DEFAULT 90)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    rows_deleted INTEGER;
BEGIN
    DELETE FROM search_queries
    WHERE searched_at < NOW() - (older_than_days || ' days')::INTERVAL;

    GET DIAGNOSTICS rows_deleted = ROW_COUNT;

    RAISE NOTICE 'Deleted % search_queries rows older than % days.', rows_deleted, older_than_days;
    RETURN rows_deleted;
END;
$$;

COMMENT ON FUNCTION prune_old_search_queries(INTEGER) IS
'Deletes search_queries rows older than the specified number of days. '
'Run periodically to prevent unbounded table growth on the free tier. '
'Default retention: 90 days.';

GRANT EXECUTE ON FUNCTION prune_old_search_queries(INTEGER) TO authenticated;


-- ── Storage capacity estimate ─────────────────────────────────────────────────
-- Each search_queries row is approximately 80–120 bytes.
-- Supabase free tier database limit: 500 MB.
-- At 100 searches/day → ~3,650 rows/year → ~438 KB/year.
-- Retention cleanup is optional for realistic student portal traffic.
-- Run prune_old_search_queries() if the table exceeds ~500,000 rows.
