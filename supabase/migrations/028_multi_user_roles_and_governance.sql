-- =============================================================================
-- Migration 028 — Multi-User Roles, Delegated Governance, Verification & Audit
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   1. Users: Add verified teacher trust level, addition attribution, and governance status.
--   2. Papers: Add safe deletion timestamp/actor, and stateful verification columns.
--   3. Content Reports: Add report categories, details, and active pending spam-prevention index.
--   4. Admin Governance Requests: Two-person approval workflow table for Admin removals.
--   5. Admin Activity Logs: Append-only immutable audit trail table decoupled from legacy Supabase Auth.
--   6. RLS Policies: Zero-trust RLS blocking PostgREST direct client queries for governance & audit.
--
-- Safe to re-run: Uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS throughout.
-- Backward Compatible: YES
-- =============================================================================

-- ── 1. Users Table Governance Columns ────────────────────────────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS is_verified_teacher BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS verified_teacher_by_uid TEXT,
    ADD COLUMN IF NOT EXISTS verified_teacher_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS admin_added_by_uid TEXT,
    ADD COLUMN IF NOT EXISTS admin_added_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS governance_status VARCHAR(30) NOT NULL DEFAULT 'active'
        CHECK (governance_status IN ('active', 'pending_removal', 'removed', 'suspended'));

CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_is_verified_teacher ON users (is_verified_teacher);
CREATE INDEX IF NOT EXISTS idx_users_governance_status ON users (governance_status);

COMMENT ON COLUMN users.is_verified_teacher IS 'True if Super Admin has personally verified and granted delegated governance trust.';
COMMENT ON COLUMN users.verified_teacher_by_uid IS 'Firebase UID of Super Admin who verified this educator.';
COMMENT ON COLUMN users.verified_teacher_at IS 'Timestamp when verified teacher trust was granted.';
COMMENT ON COLUMN users.admin_added_by_uid IS 'Firebase UID of the Admin/Super Admin who promoted this user to Admin.';
COMMENT ON COLUMN users.admin_added_at IS 'Timestamp when user was promoted to Admin.';
COMMENT ON COLUMN users.governance_status IS 'Lifecycle state: active, pending_removal, removed, suspended.';


-- ── 2. Papers Safe Deletion & Verification Columns ───────────────────────────
ALTER TABLE papers
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS deleted_by_uid TEXT,
    ADD COLUMN IF NOT EXISTS verification_status VARCHAR(30) NOT NULL DEFAULT 'NOT_VERIFIED'
        CHECK (verification_status IN ('NOT_VERIFIED', 'PENDING_VERIFICATION', 'VERIFIED', 'VERIFICATION_REVOKED')),
    ADD COLUMN IF NOT EXISTS verified_by_uid TEXT,
    ADD COLUMN IF NOT EXISTS verified_by_name TEXT,
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS verification_note TEXT;

CREATE INDEX IF NOT EXISTS idx_papers_verification_status ON papers (verification_status);
CREATE INDEX IF NOT EXISTS idx_papers_deleted_at ON papers (deleted_at);

COMMENT ON COLUMN papers.deleted_at IS 'Timestamp when paper was marked deleted / archived by Super Admin.';
COMMENT ON COLUMN papers.deleted_by_uid IS 'Firebase UID of Super Admin who performed deletion.';
COMMENT ON COLUMN papers.verification_status IS 'Content verification lifecycle: NOT_VERIFIED, PENDING_VERIFICATION, VERIFIED, VERIFICATION_REVOKED.';
COMMENT ON COLUMN papers.verified_by_uid IS 'Firebase UID of Verified Teacher or Super Admin who verified curriculum accuracy.';
COMMENT ON COLUMN papers.verified_by_name IS 'Public display name of verifier shown on paper detail.';
COMMENT ON COLUMN papers.verified_at IS 'Timestamp of verification action.';
COMMENT ON COLUMN papers.verification_note IS 'Optional editorial or verification notes from verifier.';


-- ── 3. Content Reports Lifecycle Enhancements ────────────────────────────────
ALTER TABLE content_reports
    ADD COLUMN IF NOT EXISTS report_category VARCHAR(50) DEFAULT 'other',
    ADD COLUMN IF NOT EXISTS details JSONB DEFAULT '{}'::jsonb;

-- Prevent active spam while allowing re-reporting after earlier report is resolved
CREATE UNIQUE INDEX IF NOT EXISTS uq_content_reports_active_user_target
    ON content_reports (reporter_uid, target_type, target_id)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_content_reports_target ON content_reports (target_type, target_id);

COMMENT ON COLUMN content_reports.report_category IS 'Standardized category (e.g. wrong_class, wrong_subject, copyright_issue, etc.)';
COMMENT ON COLUMN content_reports.details IS 'Structured report payload and user context.';


-- ── 4. Admin Governance Requests (Removal & Multi-Party Approvals) ───────────
CREATE TABLE IF NOT EXISTS admin_governance_requests (
    id                     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    request_type           VARCHAR(50)  NOT NULL, -- 'admin_removal', 'admin_addition'
    target_user_uid        TEXT         NOT NULL,
    target_email           VARCHAR(255) NOT NULL,
    target_name            VARCHAR(255) NOT NULL,
    initiated_by_uid       TEXT         NOT NULL,
    initiated_by_email     VARCHAR(255) NOT NULL,
    initiated_by_name      VARCHAR(255) NOT NULL,
    reason                 TEXT         NOT NULL,
    status                 VARCHAR(30)  NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled', 'overridden_by_super_admin')),
    second_approver_uid    TEXT,
    second_approver_email  VARCHAR(255),
    second_approver_name   VARCHAR(255),
    second_approved_at     TIMESTAMPTZ,
    decision_notes         TEXT,
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_governance_requests_status ON admin_governance_requests (status);
CREATE INDEX IF NOT EXISTS idx_governance_requests_target ON admin_governance_requests (target_user_uid);

COMMENT ON TABLE admin_governance_requests IS 'Governance state machine for delegated Admin removals requiring two-person approval.';


-- ── 5. Immutable Admin Activity Logs Table ───────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_activity_logs (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_uid        TEXT         NOT NULL,
    actor_email      VARCHAR(255) NOT NULL,
    actor_name       VARCHAR(255) NOT NULL,
    actor_role       VARCHAR(50)  NOT NULL,
    action           VARCHAR(100) NOT NULL,
    target_type      VARCHAR(50)  NOT NULL,
    target_id        VARCHAR(100) NOT NULL,
    target_title     TEXT,
    reason           TEXT,
    metadata         JSONB        NOT NULL DEFAULT '{}'::jsonb,
    ip_address       VARCHAR(45),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_activity_created_at ON admin_activity_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_activity_actor_uid ON admin_activity_logs (actor_uid);
CREATE INDEX IF NOT EXISTS idx_admin_activity_action ON admin_activity_logs (action);
CREATE INDEX IF NOT EXISTS idx_admin_activity_target ON admin_activity_logs (target_type, target_id);

COMMENT ON TABLE admin_activity_logs IS 'Append-only immutable audit trail of all administrative platform actions.';


-- ── 6. RLS Policies (Zero Client-Side Trust) ─────────────────────────────────
ALTER TABLE admin_governance_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_activity_logs ENABLE ROW LEVEL SECURITY;

-- Block client-side PostgREST completely; backend direct SQLAlchemy connection manages queries
DROP POLICY IF EXISTS "admin_governance_deny_client" ON admin_governance_requests;
CREATE POLICY "admin_governance_deny_client" ON admin_governance_requests FOR ALL TO public USING (false);

DROP POLICY IF EXISTS "admin_activity_deny_client" ON admin_activity_logs;
CREATE POLICY "admin_activity_deny_client" ON admin_activity_logs FOR ALL TO public USING (false);
