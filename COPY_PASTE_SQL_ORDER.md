# Copy-Paste SQL — Exact Execution Order
## TN State Board Learning Platform

**SQL Editor:** https://supabase.com/dashboard/project/fcxvrsgcvmlowehpilvr/sql/new

**Instructions:**
- Run each block in a separate query in the SQL Editor
- Click **Run** after pasting each block
- Confirm **no errors** before moving to the next block
- Run the verification query after each block

---

## BLOCK 1 of 6 — Schema (001_schema.sql)

```sql
-- =============================================================================
-- Migration 001 — Schema
-- TN State Board Learning Platform
-- =============================================================================

-- ── classes ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS classes (
    id            INTEGER      PRIMARY KEY,
    name          VARCHAR(20)  NOT NULL,
    slug          VARCHAR(10)  NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_classes_slug ON classes (slug);

COMMENT ON TABLE  classes          IS 'Tamil Nadu State Board school classes (9–12).';
COMMENT ON COLUMN classes.id       IS 'Class number used as primary key (9, 10, 11, 12).';
COMMENT ON COLUMN classes.slug     IS 'URL-safe identifier, matches class number.';


-- ── subjects ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subjects (
    id             SERIAL       PRIMARY KEY,
    class_id       INTEGER      NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    name           VARCHAR(100) NOT NULL,
    slug           VARCHAR(50)  NOT NULL,
    is_practical   BOOLEAN      NOT NULL DEFAULT false,
    display_order  INTEGER      NOT NULL DEFAULT 0,

    CONSTRAINT uq_subjects_class_slug UNIQUE (class_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_subjects_class_id ON subjects (class_id);

COMMENT ON TABLE  subjects               IS 'Subjects offered per class.';
COMMENT ON COLUMN subjects.slug          IS 'Short URL-safe identifier, unique within a class.';
COMMENT ON COLUMN subjects.is_practical  IS 'True for lab/practical subjects (Physics, Chemistry, Biology, CS, CA).';
COMMENT ON COLUMN subjects.display_order IS 'Ascending display order within a class.';


-- ── papers ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS papers (
    id              SERIAL        PRIMARY KEY,
    subject_id      INTEGER       NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    exam_type       VARCHAR(100)  NOT NULL,
    year            INTEGER       NOT NULL,
    title           VARCHAR(255)  NOT NULL,
    paper_type      VARCHAR(20)   NOT NULL
                    CHECK (paper_type IN ('question', 'answer_key')),
    file_path       VARCHAR(500),
    public_url      TEXT,
    youtube_url     TEXT,
    is_visible      BOOLEAN       NOT NULL DEFAULT true,
    download_count  INTEGER       NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_papers_subject_title_year_exam
        UNIQUE (subject_id, title, year, exam_type)
);

CREATE INDEX IF NOT EXISTS idx_papers_subject_id   ON papers (subject_id);
CREATE INDEX IF NOT EXISTS idx_papers_is_visible   ON papers (is_visible);
CREATE INDEX IF NOT EXISTS idx_papers_created_at   ON papers (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_papers_download_cnt ON papers (download_count DESC);
CREATE INDEX IF NOT EXISTS idx_papers_exam_type    ON papers (exam_type);
CREATE INDEX IF NOT EXISTS idx_papers_year         ON papers (year);

COMMENT ON TABLE  papers              IS 'Uploaded question papers and answer keys.';
COMMENT ON COLUMN papers.paper_type   IS '"question" = question paper, "answer_key" = answer/solution.';
COMMENT ON COLUMN papers.file_path    IS 'Supabase Storage object key — used only for deletion.';
COMMENT ON COLUMN papers.public_url   IS 'Supabase Storage public CDN URL — used by the browser.';
COMMENT ON COLUMN papers.is_visible   IS 'When false, paper is hidden from public view but retained for admin.';


-- ── audit_logs ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id               SERIAL        PRIMARY KEY,
    admin_id         UUID          REFERENCES auth.users(id) ON DELETE SET NULL,
    admin_email      VARCHAR(255),
    action           VARCHAR(50)   NOT NULL,
    target_paper_id  INTEGER       REFERENCES papers(id) ON DELETE SET NULL,
    target_details   JSONB,
    ip_address       VARCHAR(45),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action     ON audit_logs (action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_id   ON audit_logs (admin_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs (created_at DESC);

COMMENT ON TABLE  audit_logs                 IS 'Immutable admin action history.';
COMMENT ON COLUMN audit_logs.admin_id        IS 'auth.users.id — NULL if the user was deleted.';
COMMENT ON COLUMN audit_logs.admin_email     IS 'Denormalised email, retained after user deletion.';
COMMENT ON COLUMN audit_logs.target_details  IS 'JSONB payload: {"title": "…", "changes": {…}}.';


-- ── search_queries ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS search_queries (
    id            SERIAL        PRIMARY KEY,
    term          VARCHAR(255)  NOT NULL,
    result_count  INTEGER       NOT NULL DEFAULT 0,
    searched_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_queries_term        ON search_queries (term);
CREATE INDEX IF NOT EXISTS idx_search_queries_searched_at ON search_queries (searched_at DESC);

COMMENT ON TABLE  search_queries              IS 'Every search performed by a public user.';
COMMENT ON COLUMN search_queries.term         IS 'Raw search term as typed by the user.';
COMMENT ON COLUMN search_queries.result_count IS 'Number of papers returned for this search.';
```

**Verification — run immediately after Block 1:**
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Expected: audit_logs, classes, papers, search_queries, subjects
```

---

## BLOCK 2 of 6 — Seed Data (002_seed_data.sql)

```sql
-- =============================================================================
-- Migration 002 — Seed Data
-- TN State Board Learning Platform
-- =============================================================================

-- ── Classes ──────────────────────────────────────────────────────────────────
INSERT INTO classes (id, name, slug) VALUES
    (9,  'Class 9',  '9'),
    (10, 'Class 10', '10'),
    (11, 'Class 11', '11'),
    (12, 'Class 12', '12')
ON CONFLICT (id) DO NOTHING;


-- ── Subjects — Class 9 ───────────────────────────────────────────────────────
INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (9, 'Tamil',          'tamil',   false, 1),
    (9, 'English',        'english', false, 2),
    (9, 'Mathematics',    'maths',   false, 3),
    (9, 'Science',        'science', true,  4),
    (9, 'Social Science', 'social',  false, 5)
ON CONFLICT (class_id, slug) DO NOTHING;


-- ── Subjects — Class 10 ──────────────────────────────────────────────────────
INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (10, 'Tamil',          'tamil',   false, 1),
    (10, 'English',        'english', false, 2),
    (10, 'Mathematics',    'maths',   false, 3),
    (10, 'Science',        'science', true,  4),
    (10, 'Social Science', 'social',  false, 5)
ON CONFLICT (class_id, slug) DO NOTHING;


-- ── Subjects — Class 11 ──────────────────────────────────────────────────────
INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (11, 'Tamil',                 'tamil',     false,  1),
    (11, 'English',               'english',   false,  2),
    (11, 'Mathematics',           'maths',     false,  3),
    (11, 'Physics',               'physics',   true,   4),
    (11, 'Chemistry',             'chemistry', true,   5),
    (11, 'Biology',               'biology',   true,   6),
    (11, 'Computer Science',      'cs',        true,   7),
    (11, 'Computer Applications', 'ca',        true,   8),
    (11, 'Accountancy',           'acc',       false,  9),
    (11, 'Commerce',              'comm',      false, 10),
    (11, 'Economics',             'eco',       false, 11)
ON CONFLICT (class_id, slug) DO NOTHING;


-- ── Subjects — Class 12 ──────────────────────────────────────────────────────
INSERT INTO subjects (class_id, name, slug, is_practical, display_order) VALUES
    (12, 'Tamil',                 'tamil',     false,  1),
    (12, 'English',               'english',   false,  2),
    (12, 'Mathematics',           'maths',     false,  3),
    (12, 'Physics',               'physics',   true,   4),
    (12, 'Chemistry',             'chemistry', true,   5),
    (12, 'Biology',               'biology',   true,   6),
    (12, 'Computer Science',      'cs',        true,   7),
    (12, 'Computer Applications', 'ca',        true,   8),
    (12, 'Accountancy',           'acc',       false,  9),
    (12, 'Commerce',              'comm',      false, 10),
    (12, 'Economics',             'eco',       false, 11)
ON CONFLICT (class_id, slug) DO NOTHING;
```

**Verification — run immediately after Block 2:**
```sql
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;
-- Expected: class_count = 4, subject_count = 32
```

---

## BLOCK 3 of 6 — RLS Policies (003_rls_policies.sql)

```sql
-- =============================================================================
-- Migration 003 — Row Level Security Policies
-- TN State Board Learning Platform
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
    ON classes
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "classes_admin_all"
    ON classes
    FOR ALL
    TO authenticated
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);


-- SUBJECTS
DROP POLICY IF EXISTS "subjects_public_read" ON subjects;
DROP POLICY IF EXISTS "subjects_admin_all"   ON subjects;

CREATE POLICY "subjects_public_read"
    ON subjects
    FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "subjects_admin_all"
    ON subjects
    FOR ALL
    TO authenticated
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);


-- PAPERS
DROP POLICY IF EXISTS "papers_public_read"   ON papers;
DROP POLICY IF EXISTS "papers_admin_read"    ON papers;
DROP POLICY IF EXISTS "papers_admin_insert"  ON papers;
DROP POLICY IF EXISTS "papers_admin_update"  ON papers;
DROP POLICY IF EXISTS "papers_admin_delete"  ON papers;

CREATE POLICY "papers_public_read"
    ON papers
    FOR SELECT
    TO anon
    USING (is_visible = true);

CREATE POLICY "papers_admin_read"
    ON papers
    FOR SELECT
    TO authenticated
    USING (auth.uid() IS NOT NULL);

CREATE POLICY "papers_admin_insert"
    ON papers
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "papers_admin_update"
    ON papers
    FOR UPDATE
    TO authenticated
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "papers_admin_delete"
    ON papers
    FOR DELETE
    TO authenticated
    USING (auth.uid() IS NOT NULL);


-- AUDIT LOGS
DROP POLICY IF EXISTS "audit_logs_admin_read"   ON audit_logs;
DROP POLICY IF EXISTS "audit_logs_admin_insert"  ON audit_logs;

CREATE POLICY "audit_logs_admin_read"
    ON audit_logs
    FOR SELECT
    TO authenticated
    USING (auth.uid() IS NOT NULL);

CREATE POLICY "audit_logs_admin_insert"
    ON audit_logs
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL);


-- SEARCH QUERIES
DROP POLICY IF EXISTS "search_queries_public_insert" ON search_queries;
DROP POLICY IF EXISTS "search_queries_admin_read"    ON search_queries;

CREATE POLICY "search_queries_public_insert"
    ON search_queries
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "search_queries_admin_read"
    ON search_queries
    FOR SELECT
    TO authenticated
    USING (auth.uid() IS NOT NULL);
```

**Verification — run immediately after Block 3:**
```sql
SELECT COUNT(*) AS policy_count
FROM pg_policies
WHERE schemaname = 'public';
-- Expected: 13
```

---

## BLOCK 4 of 6 — Functions (004_functions.sql)

```sql
-- =============================================================================
-- Migration 004 — Database Functions (RPC)
-- TN State Board Learning Platform
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

COMMENT ON FUNCTION increment_download_count(INTEGER) IS
'Atomically increments download_count for a visible paper. '
'Safe to call as anon — SECURITY DEFINER restricts the operation to this one column.';


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
        (SELECT COUNT(*)                          FROM papers)                          AS total_papers,
        (SELECT COALESCE(SUM(download_count), 0)  FROM papers)                          AS total_downloads,
        (SELECT COUNT(*)                          FROM subjects)                        AS total_subjects,
        (SELECT COUNT(*)                          FROM classes)                         AS total_classes,
        (SELECT COUNT(*) FROM papers WHERE is_visible = true)                           AS visible_papers,
        (SELECT COUNT(*) FROM papers WHERE paper_type = 'question')                     AS question_papers,
        (SELECT COUNT(*) FROM papers WHERE paper_type = 'answer_key')                   AS answer_keys;
END;
$$;

COMMENT ON FUNCTION get_admin_stats() IS
'Returns platform-wide statistics for the admin dashboard in one round-trip.';


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

COMMENT ON FUNCTION get_search_analytics() IS
'Aggregates search_queries into popular and recent searches for the admin dashboard.';


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
    v_result    JSONB := '[]'::JSONB;
    v_class     RECORD;
    v_subj      RECORD;
    v_coverage  JSONB;
    v_subjects  JSONB := '[]'::JSONB;
    v_classes   JSONB := '[]'::JSONB;
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


-- Grants
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION increment_download_count(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION get_admin_stats()                 TO authenticated;
GRANT EXECUTE ON FUNCTION get_search_analytics()            TO authenticated;
GRANT EXECUTE ON FUNCTION get_content_status()              TO authenticated;
```

**Verification — run immediately after Block 4:**
```sql
SELECT * FROM get_admin_stats();
-- Expected: 1 row — total_classes=4, total_subjects=32, all paper counts=0
```

---

## BLOCK 5 of 6 — Search Analytics (005_search_analytics.sql)

```sql
-- =============================================================================
-- Migration 005 — Search Analytics Indexes and Retention Policy
-- TN State Board Learning Platform
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

COMMENT ON VIEW search_term_counts IS
'Aggregated search term frequency — top 100 terms by search count.';


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
'Deletes search_queries rows older than the specified number of days. Default: 90 days.';

GRANT EXECUTE ON FUNCTION prune_old_search_queries(INTEGER) TO authenticated;
```

**Verification — run immediately after Block 5:**
```sql
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';
-- Expected: search_term_counts
```

---

## BLOCK 6 of 6 — Search RPC (006_search_rpc.sql)

```sql
-- =============================================================================
-- Migration 006 — Full-Text Search RPC
-- TN State Board Learning Platform
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
      AND (p_class_id   IS NULL OR c.id         = p_class_id)
      AND (p_exam_type  IS NULL OR p.exam_type  = p_exam_type)
      AND (p_paper_type IS NULL OR p.paper_type = p_paper_type)
    ORDER BY p.created_at DESC
    LIMIT 50;
END;
$$;

COMMENT ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) IS
'Searches papers across title, exam_type, subject name, and class name using ILIKE.';

GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION search_papers(TEXT, INTEGER, TEXT, TEXT) TO authenticated;
```

**Verification — run immediately after Block 6:**
```sql
SELECT * FROM search_papers('maths', NULL, NULL, NULL);
-- Expected: 0 rows, NO ERROR (empty result is correct — no papers uploaded yet)
```

---

## BLOCK 7 — Storage Bucket RLS Policies
### (Run AFTER creating the `papers` bucket in Storage UI)

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

## FINAL VERIFICATION — Run this last to confirm everything

```sql
-- 1. All 5 tables present
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
-- Expected: audit_logs, classes, papers, search_queries, subjects

-- 2. All 6 functions present
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY routine_name;
-- Expected: get_admin_stats, get_content_status, get_search_analytics,
--           increment_download_count, prune_old_search_queries, search_papers

-- 3. 13 RLS policies
SELECT COUNT(*) AS policy_count
FROM pg_policies
WHERE schemaname = 'public';
-- Expected: 13

-- 4. 1 view
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'public';
-- Expected: search_term_counts

-- 5. Seed data correct
SELECT
  (SELECT COUNT(*) FROM classes)  AS class_count,
  (SELECT COUNT(*) FROM subjects) AS subject_count;
-- Expected: 4, 32

-- 6. Stats RPC works
SELECT * FROM get_admin_stats();
-- Expected: total_classes=4, total_subjects=32, others=0

-- 7. Search RPC works
SELECT * FROM search_papers('maths', NULL, NULL, NULL);
-- Expected: 0 rows, no error
```

**All 7 checks passing = database is fully ready. Proceed to upload papers and deploy.**
