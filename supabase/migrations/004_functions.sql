-- =============================================================================
-- Migration 004 — Database Functions (RPC)
-- TN State Board Learning Platform
-- =============================================================================
-- Creates PostgreSQL functions callable from the Supabase JS client via
-- supabase.rpc('function_name', { param: value }).
--
-- All functions use SECURITY DEFINER so they execute with the privileges
-- of the function owner (postgres), not the calling role (anon/authenticated).
-- This allows controlled privilege escalation without opening RLS to everyone.
-- =============================================================================


-- =============================================================================
-- increment_download_count
-- =============================================================================
-- Atomically increments papers.download_count for a visible paper.
--
-- Why a function instead of a direct UPDATE?
--   The papers table does not grant UPDATE to the anon role (students can't
--   edit papers). Using SECURITY DEFINER lets anon call this one controlled
--   operation without widening UPDATE permission on the entire table.
--
-- Called from: frontend/src/services/papers.js
--   supabase.rpc('increment_download_count', { paper_id_param: 42 })
--
-- Returns: void (ignore the return value)

CREATE OR REPLACE FUNCTION increment_download_count(paper_id_param INTEGER)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE papers
    SET    download_count = download_count + 1
    WHERE  id = paper_id_param
      AND  is_visible = true;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Paper not found or not visible (id=%)', paper_id_param;
    END IF;
END;
$$;

COMMENT ON FUNCTION increment_download_count(INTEGER) IS
'Atomically increments download_count for a visible paper. '
'Safe to call as anon — SECURITY DEFINER restricts the operation to this one column.';


-- =============================================================================
-- get_admin_stats
-- =============================================================================
-- Returns aggregate stats for the admin dashboard in a single RPC call.
-- Avoids 7 separate SELECT COUNT(*) round-trips from the browser.
--
-- Equivalent to FastAPI's GET /admin/stats
--
-- Called from: frontend/src/services/admin.js
--   supabase.rpc('get_admin_stats')
--
-- Returns: one row with all stat columns.

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
        (SELECT COUNT(*)                                             FROM papers)                              AS total_papers,
        (SELECT COALESCE(SUM(download_count), 0)                    FROM papers)                              AS total_downloads,
        (SELECT COUNT(*)                                             FROM subjects)                            AS total_subjects,
        (SELECT COUNT(*)                                             FROM classes)                             AS total_classes,
        (SELECT COUNT(*)                           FROM papers WHERE is_visible = true)                       AS visible_papers,
        (SELECT COUNT(*)                           FROM papers WHERE paper_type = 'question')                 AS question_papers,
        (SELECT COUNT(*)                           FROM papers WHERE paper_type = 'answer_key')               AS answer_keys;
END;
$$;

COMMENT ON FUNCTION get_admin_stats() IS
'Returns platform-wide statistics for the admin dashboard in one round-trip.';


-- =============================================================================
-- get_search_analytics
-- =============================================================================
-- Returns popular and recent search terms from the search_queries table.
-- Replaces the in-memory analytics.py module.
--
-- Called from: frontend/src/services/admin.js
--   supabase.rpc('get_search_analytics')
--
-- Returns: JSONB with popular_searches and recent_searches arrays.

CREATE OR REPLACE FUNCTION get_search_analytics()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_popular JSONB;
    v_recent  JSONB;
BEGIN
    -- Top 20 terms by frequency
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object('term', term, 'count', cnt)
            ORDER BY cnt DESC
        ),
        '[]'::JSONB
    )
    INTO v_popular
    FROM (
        SELECT   LOWER(TRIM(term)) AS term,
                 COUNT(*)          AS cnt
        FROM     search_queries
        GROUP BY LOWER(TRIM(term))
        ORDER BY cnt DESC
        LIMIT    20
    ) sub;

    -- 20 most recent searches with result counts
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'term',         term,
                'result_count', result_count,
                'searched_at',  searched_at
            )
            ORDER BY searched_at DESC
        ),
        '[]'::JSONB
    )
    INTO v_recent
    FROM (
        SELECT term, result_count, searched_at
        FROM   search_queries
        ORDER  BY searched_at DESC
        LIMIT  20
    ) sub;

    RETURN jsonb_build_object(
        'popular_searches', v_popular,
        'recent_searches',  v_recent
    );
END;
$$;

COMMENT ON FUNCTION get_search_analytics() IS
'Aggregates search_queries into popular and recent searches for the admin dashboard. '
'Replaces the in-memory analytics.py module — results are now durable across restarts.';


-- =============================================================================
-- get_content_status
-- =============================================================================
-- Returns a coverage matrix: for each class > subject, which exam types
-- have at least one paper uploaded.
--
-- Equivalent to FastAPI's GET /admin/content-status
-- Called from: frontend/src/services/admin.js
--   supabase.rpc('get_content_status')

CREATE OR REPLACE FUNCTION get_content_status()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_tracked_types TEXT[] := ARRAY[
        'Annual Exam',
        'Half Yearly Exam',
        'Quarterly Exam',
        'Unit Test 1',
        'Unit Test 2',
        'Unit Test 3'
    ];
    v_result JSONB := '[]'::JSONB;
    v_class  RECORD;
    v_subj   RECORD;
    v_coverage JSONB;
    v_subjects JSONB := '[]'::JSONB;
    v_classes  JSONB := '[]'::JSONB;
    v_exam_type TEXT;
    v_has_paper BOOLEAN;
BEGIN
    FOR v_class IN
        SELECT id, name FROM classes ORDER BY id
    LOOP
        v_subjects := '[]'::JSONB;

        FOR v_subj IN
            SELECT id, name
            FROM   subjects
            WHERE  class_id = v_class.id
            ORDER  BY display_order
        LOOP
            v_coverage := '{}'::JSONB;

            FOREACH v_exam_type IN ARRAY v_tracked_types
            LOOP
                SELECT EXISTS (
                    SELECT 1 FROM papers
                    WHERE  subject_id = v_subj.id
                      AND  exam_type  = v_exam_type
                )
                INTO v_has_paper;

                v_coverage := v_coverage || jsonb_build_object(v_exam_type, v_has_paper);
            END LOOP;

            v_subjects := v_subjects || jsonb_build_array(
                jsonb_build_object(
                    'id',       v_subj.id,
                    'name',     v_subj.name,
                    'coverage', v_coverage
                )
            );
        END LOOP;

        v_classes := v_classes || jsonb_build_array(
            jsonb_build_object(
                'id',       v_class.id,
                'name',     v_class.name,
                'subjects', v_subjects
            )
        );
    END LOOP;

    RETURN jsonb_build_object(
        'exam_types', to_jsonb(v_tracked_types),
        'classes',    v_classes
    );
END;
$$;

COMMENT ON FUNCTION get_content_status() IS
'Returns a class > subject > exam_type coverage matrix for the admin Content Status page.';


-- =============================================================================
-- GRANT EXECUTE PERMISSIONS
-- =============================================================================
-- anon can call: increment_download_count (one controlled write, no RLS bypass)
-- authenticated can call: all functions

GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_admin_stats()                 TO authenticated;
GRANT EXECUTE ON FUNCTION get_search_analytics()            TO authenticated;
GRANT EXECUTE ON FUNCTION get_content_status()              TO authenticated;
