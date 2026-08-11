-- =============================================================================
-- Migration 021 — Grant service_role Privileges
-- TN State Board Learning Platform
-- =============================================================================
-- Grants the minimum required privileges to service_role for tables created
-- in migration 019, allowing the backend admin_db client to perform DML.
-- =============================================================================

-- Backend auth.py uses SELECT and INSERT to fetch/create user profiles
GRANT SELECT, INSERT ON public.users TO service_role;

-- Backend papers_service.py uses INSERT to record download tracking
GRANT INSERT ON public.download_logs TO service_role;
