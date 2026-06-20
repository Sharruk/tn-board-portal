-- =============================================================================
-- Migration 003 — Row Level Security Policies
-- TN State Board Learning Platform
-- =============================================================================
-- Enables RLS on all tables and defines who can read/write what.
--
-- Roles used:
--   anon          — unauthenticated public users (students browsing the portal)
--   authenticated — a signed-in Supabase Auth user (the admin)
--
-- Key principle: the anon key is safe to embed in the frontend bundle because
-- RLS policies enforce all access rules at the database level — not in app code.
-- =============================================================================


-- ── Enable RLS on every table ────────────────────────────────────────────────
-- Must be done before any policy takes effect.

ALTER TABLE classes        ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects       ENABLE ROW LEVEL SECURITY;
ALTER TABLE papers         ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_queries ENABLE ROW LEVEL SECURITY;


-- =============================================================================
-- CLASSES
-- =============================================================================
-- Public: everyone can read all classes (4 rows, static reference data).
-- Write:  only authenticated admins can insert/update/delete.
--         In practice, classes never change after seeding.

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


-- =============================================================================
-- SUBJECTS
-- =============================================================================
-- Public: everyone can read all subjects.
-- Write:  only authenticated admins.

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


-- =============================================================================
-- PAPERS
-- =============================================================================
-- Public SELECT:  only rows where is_visible = true.
--                 Hidden papers are invisible to the public.
-- Admin SELECT:   all rows regardless of is_visible.
-- Admin INSERT:   any authenticated user.
-- Admin UPDATE:   any authenticated user.
-- Admin DELETE:   any authenticated user.
--
-- IMPORTANT: Download count increments use a SECURITY DEFINER RPC function
--            (see 004_functions.sql) so anon users never need UPDATE permission
--            on this table directly.

DROP POLICY IF EXISTS "papers_public_read"   ON papers;
DROP POLICY IF EXISTS "papers_admin_read"    ON papers;
DROP POLICY IF EXISTS "papers_admin_insert"  ON papers;
DROP POLICY IF EXISTS "papers_admin_update"  ON papers;
DROP POLICY IF EXISTS "papers_admin_delete"  ON papers;

-- Public can only see visible papers
CREATE POLICY "papers_public_read"
    ON papers
    FOR SELECT
    TO anon
    USING (is_visible = true);

-- Admin can see all papers (including hidden)
CREATE POLICY "papers_admin_read"
    ON papers
    FOR SELECT
    TO authenticated
    USING (auth.uid() IS NOT NULL);

-- Admin can upload new papers
CREATE POLICY "papers_admin_insert"
    ON papers
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() IS NOT NULL);

-- Admin can edit metadata and toggle visibility
CREATE POLICY "papers_admin_update"
    ON papers
    FOR UPDATE
    TO authenticated
    USING (auth.uid() IS NOT NULL)
    WITH CHECK (auth.uid() IS NOT NULL);

-- Admin can delete papers
CREATE POLICY "papers_admin_delete"
    ON papers
    FOR DELETE
    TO authenticated
    USING (auth.uid() IS NOT NULL);


-- =============================================================================
-- AUDIT LOGS
-- =============================================================================
-- Public:    no access at all.
-- Admin READ:   authenticated users can read the full audit trail.
-- Admin INSERT: authenticated users can append log entries.
--               No UPDATE or DELETE — audit logs are append-only.
--
-- Note: Audit logging is client-driven (the React admin app inserts rows).
--       This is sufficient for a student project. A production system would
--       use database triggers for tamper-proof server-side enforcement.

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


-- =============================================================================
-- SEARCH QUERIES
-- =============================================================================
-- Public INSERT: any anonymous user can log a search term.
--               This replaces the in-memory analytics.py deque.
-- Public SELECT: blocked — students cannot read each other's searches.
-- Admin SELECT:  authenticated admins can read the full analytics table.
-- No UPDATE or DELETE by anyone — analytics rows are append-only.

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


-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================
-- Run these after applying to confirm all policies are active:
--
--   SELECT tablename, policyname, cmd, roles
--   FROM pg_policies
--   WHERE schemaname = 'public'
--   ORDER BY tablename, cmd;
--
-- Expected output: 12 policies across 5 tables.
