-- =============================================================================
-- Migration 009 — Fix official_notices Table Privileges
-- TN State Board Student Portal
-- =============================================================================
-- ROOT CAUSE:
--   The `official_notices` table was created on a Supabase project where the
--   default PUBLIC schema privilege has been revoked. This means PostgreSQL
--   checks role-level table GRANTs BEFORE evaluating RLS policies.
--
--   The `papers` table works because it was created earlier when the default
--   PUBLIC schema grant was still active. `official_notices` was created after
--   that grant was revoked, so it has zero table-level privileges for the
--   `anon` and `authenticated` roles — causing "permission denied for table
--   official_notices" even though the RLS policies are correctly defined.
--
-- THE FIX:
--   Explicitly grant the necessary table privileges to the `anon` and
--   `authenticated` roles. RLS policies (already in place from migration 008)
--   then enforce fine-grained row-level access on top of these grants.
--
-- PRIVILEGE MODEL:
--   anon         — SELECT only (students browsing, filtered by RLS)
--   authenticated — SELECT, INSERT, UPDATE, DELETE (admin, filtered by RLS)
--   SEQUENCE     — authenticated needs USAGE to let SERIAL auto-increment work
-- =============================================================================

-- ── Table privileges ──────────────────────────────────────────────────────────

-- anon role: read-only access (RLS filters to is_visible=true + non-expired)
GRANT SELECT ON official_notices TO anon;

-- authenticated role: full CRUD (RLS allows all rows for admin)
GRANT SELECT, INSERT, UPDATE, DELETE ON official_notices TO authenticated;

-- SERIAL primary key — authenticated needs sequence access for INSERT
GRANT USAGE, SELECT ON SEQUENCE official_notices_id_seq TO authenticated;

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- After running this migration, execute in the SQL Editor to confirm:
--
--   SELECT grantee, privilege_type
--   FROM   information_schema.role_table_grants
--   WHERE  table_name = 'official_notices'
--   ORDER  BY grantee, privilege_type;
--
-- Expected output:
--   anon          | SELECT
--   authenticated | DELETE
--   authenticated | INSERT
--   authenticated | SELECT
--   authenticated | UPDATE
-- =============================================================================
