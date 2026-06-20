# Supabase Deployment Checklist
## TN State Board Learning Platform

**Date:** 2026-06-20  
**Project URL:** https://fcxvrsgcvmlowehpilvr.supabase.co

---

## How to run SQL

1. Open [Supabase Dashboard](https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr)
2. Left sidebar → **SQL Editor** → **New query**
3. Paste the SQL block, click **Run**
4. Confirm no errors before moving to the next step
5. Run the verification query at the end of each step

---

## Pre-flight: Confirm what is already applied

Run this first. It tells you exactly what exists before you change anything.

```sql
-- Tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Functions
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;

-- RLS policies
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;

-- Seed data
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;

-- Views
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';
```

**Expected pre-flight results (already applied):**
- Tables: `audit_logs`, `classes`, `papers`, `search_queries`, `subjects`
- Functions: none yet
- Policies: 13 rows (if 003 applied) or 0 rows (if 003 not yet applied)
- Seed: `class_count = 4`, `subject_count = 32`
- Views: none yet

---

## STEP 1 — Verify / Apply RLS Policies (Migration 003)

> **Skip this step if the pre-flight shows 13 policies already present.**  
> **Run it if policies = 0.** It is safe to re-run: all policies use `DROP IF EXISTS` before recreating.

```sql
-- =============================================================================
-- Migration 003 — Row Level Security Policies
-- =============================================================================

-- Enable RLS on every table
ALTER TABLE classes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects       ENABLE ROW LEVEL SECURITY;
ALTER TABLE papers         ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_queries ENABLE ROW LEVEL SECURITY;

-- CLASSES
DROP POLICY IF EXISTS "classes_public_read"  ON classes;
DROP POLICY IF EXISTS "classes_admin_all"    ON classes;

CREATE POLICY "classes_public_read"
    ON classes FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "classes_admin_all"
    ON classes FOR ALL TO authenticated
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

-- SUBJECTS
DROP POLICY IF EXISTS "subjects_public_read" ON subjects;
DROP POLICY IF EXISTS "subjects_admin_all"   ON subjects;

CREATE POLICY "subjects_public_read"
    ON subjects FOR SELECT TO anon, authenticated USING (true);

CREATE POLICY "subjects_admin_all"
    ON subjects FOR ALL TO authenticated
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

-- PAPERS
DROP POLICY IF EXISTS "papers_public_read"   ON papers;
DROP POLICY IF EXISTS "papers_admin_read"    ON papers;
DROP POLICY IF EXISTS "papers_admin_insert"  ON papers;
DROP POLICY IF EXISTS "papers_admin_update"  ON papers;
DROP POLICY IF EXISTS "papers_admin_delete"  ON papers;

CREATE POLICY "papers_public_read"
    ON papers FOR SELECT TO anon
    USING (is_visible = true);

CREATE POLICY "papers_admin_read"
    ON papers FOR SELECT TO authenticated
    USING (auth.uid() IS NOT NULL);

CREATE POLICY "papers_admin_insert"
    ON papers FOR INSERT TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "papers_admin_update"
    ON papers FOR UPDATE TO authenticated
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "papers_admin_delete"
    ON papers FOR DELETE TO authenticated
    USING (auth.uid() IS NOT NULL);

-- AUDIT LOGS
DROP POLICY IF EXISTS "audit_logs_admin_read"   ON audit_logs;
DROP POLICY IF EXISTS "audit_logs_admin_insert"  ON audit_logs;

CREATE POLICY "audit_logs_admin_read"
    ON audit_logs FOR SELECT TO authenticated
    USING (auth.uid() IS NOT NULL);

CREATE POLICY "audit_logs_admin_insert"
    ON audit_logs FOR INSERT TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL);

-- SEARCH QUERIES
DROP POLICY IF EXISTS "search_queries_public_insert" ON search_queries;
DROP POLICY IF EXISTS "search_queries_admin_read"    ON search_queries;

CREATE POLICY "search_queries_public_insert"
    ON search_queries FOR INSERT TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "search_queries_admin_read"
    ON search_queries FOR SELECT TO authenticated
    USING (auth.uid() IS NOT NULL);
```

**Verification — run after Step 1:**
```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;
-- Expected: 13 rows across 5 tables
```

---

## STEP 2 — Apply Database Functions (Migration 004)

> **Must run.** Creates `increment_download_count`, `get_admin_stats`, `get_search_analytics`, `get_content_status`. Safe to re-run: uses `CREATE OR REPLACE FUNCTION`.

```sql
-- =============================================================================
-- Migration 004 — Database Functions (RPC)
-- =============================================================================

-- increment_download_count
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

-- get_admin_stats
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
        (SELECT COUNT(*)                                          FROM papers)                            AS total_papers,
        (SELECT COALESCE(SUM(download_count), 0)                 FROM papers)                            AS total_downloads,
        (SELECT COUNT(*)                                          FROM subjects)                          AS total_subjects,
        (SELECT COUNT(*)                                          FROM classes)                           AS total_classes,
        (SELECT COUNT(*)              FROM papers WHERE is_visible = true)                                AS visible_papers,
        (SELECT COUNT(*)              FROM papers WHERE paper_type = 'question')                          AS question_papers,
        (SELECT COUNT(*)              FROM papers WHERE paper_type = 'answer_key')                        AS answer_keys;
END;
$$;

-- get_search_analytics
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

-- get_content_status
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
    v_result   JSONB := '[]'::JSONB;
    v_class    RECORD;
    v_subj     RECORD;
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

-- Grants
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_admin_stats()                 TO authenticated;
GRANT EXECUTE ON FUNCTION get_search_analytics()            TO authenticated;
GRANT EXECUTE ON FUNCTION get_content_status()              TO authenticated;
```

**Verification — run after Step 2:**
```sql
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;
-- Expected: get_admin_stats, get_content_status, get_search_analytics, increment_download_count

-- Quick functional test (should return one row of stats):
SELECT * FROM get_admin_stats();
-- Expected: total_classes=4, total_subjects=32, total_papers=0 (no papers uploaded yet)
```

---

## STEP 3 — Apply Search Analytics (Migration 005)

> **Must run.** Creates the normalised search index, `search_term_counts` view, and `prune_old_search_queries` cleanup function. Safe to re-run: uses `CREATE OR REPLACE` / `CREATE INDEX IF NOT EXISTS`.

```sql
-- =============================================================================
-- Migration 005 — Search Analytics Indexes and Retention Policy
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_search_queries_normalised_term
    ON search_queries (LOWER(TRIM(term)));

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

GRANT EXECUTE ON FUNCTION prune_old_search_queries(INTEGER) TO authenticated;
```

**Verification — run after Step 3:**
```sql
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';
-- Expected: search_term_counts

SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public' AND routine_name = 'prune_old_search_queries';
-- Expected: 1 row
```

---

## STEP 4 — Apply Search RPC (Migration 006)

> **Must run.** Creates `search_papers()` — the cross-table full-text search function used by the search page. Safe to re-run: uses `CREATE OR REPLACE FUNCTION`.

```sql
-- =============================================================================
-- Migration 006 — Full-Text Search RPC
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

GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO authenticated;
```

**Verification — run after Step 4:**
```sql
-- Confirm function exists
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public' AND routine_name = 'search_papers';
-- Expected: 1 row

-- Functional test (returns empty array when no papers uploaded — this is correct)
SELECT search_papers('maths', NULL, NULL, NULL);
-- Expected: empty result set (no error)
```

---

## STEP 5 — Storage Bucket (Manual — Supabase Dashboard UI)

The `papers` storage bucket must exist for PDF uploads to work.

**Check if it exists:**  
Supabase Dashboard → **Storage** → confirm bucket named `papers` is listed.

**If it does NOT exist, create it:**

1. Storage → **New bucket**
2. Name: `papers`
3. Public bucket: **ON**
4. File size limit: `52428800` (50 MB)
5. Allowed MIME types: `application/pdf`
6. Click **Create bucket**

**Then add storage RLS policies** in Storage → Policies → `papers` bucket:

```sql
-- Allow public downloads
CREATE POLICY "papers_bucket_public_read"
ON storage.objects FOR SELECT
TO anon, authenticated
USING (bucket_id = 'papers');

-- Allow admin uploads
CREATE POLICY "papers_bucket_admin_insert"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'papers' AND auth.uid() IS NOT NULL);

-- Allow admin deletions
CREATE POLICY "papers_bucket_admin_delete"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'papers' AND auth.uid() IS NOT NULL);
```

---

## STEP 6 — Create Admin User (if not already done)

1. Supabase Dashboard → **Authentication** → **Users** → **Add user** → **Create new user**
2. Enter your admin email and a strong password (12+ chars)
3. Check **"Auto-confirm user"**
4. Click **Create User**

---

## Final Verification — Run All Checks

```sql
-- 1. Tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Expected: audit_logs, classes, papers, search_queries, subjects

-- 2. All functions
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;
-- Expected: get_admin_stats, get_content_status, get_search_analytics,
--           increment_download_count, prune_old_search_queries, search_papers

-- 3. RLS policies
SELECT COUNT(*) AS policy_count
FROM pg_policies
WHERE schemaname = 'public';
-- Expected: 13

-- 4. Views
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';
-- Expected: search_term_counts

-- 5. Seed data
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;
-- Expected: 4, 32

-- 6. Stats function works
SELECT * FROM get_admin_stats();
-- Expected: one row, total_classes=4, total_subjects=32

-- 7. Search function works (empty is correct — no papers yet)
SELECT * FROM search_papers('maths', NULL, NULL, NULL);
-- Expected: 0 rows, no error
```

---

## Expected State After All Steps

| Item | Expected |
|---|---|
| Tables | 5 (classes, subjects, papers, audit_logs, search_queries) |
| RLS policies | 13 |
| Functions | 6 (increment_download_count, get_admin_stats, get_search_analytics, get_content_status, prune_old_search_queries, search_papers) |
| Views | 1 (search_term_counts) |
| Storage bucket | `papers` (public, 50 MB limit, PDF only) |
| Admin user | 1 confirmed user in Authentication |
| App status | ✅ Fully functional — no 404s |

---

## Execution Order Summary

| Order | Action | Where |
|---|---|---|
| 1 | Run pre-flight verification query | SQL Editor |
| 2 | Run Step 1 (003 RLS) if policies = 0 | SQL Editor |
| 3 | Run Step 2 (004 functions) | SQL Editor |
| 4 | Run Step 3 (005 analytics) | SQL Editor |
| 5 | Run Step 4 (006 search RPC) | SQL Editor |
| 6 | Create `papers` storage bucket | Storage UI |
| 7 | Add storage RLS policies | SQL Editor |
| 8 | Create admin user | Authentication UI |
| 9 | Run final verification block | SQL Editor |
