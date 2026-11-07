-- =============================================================================
-- Migration 030 — Admin Team Group Chat
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   1. Admin Group Messages: Dedicated table for shared internal admin group chat.
--   2. Strict Row Level Security: Deny direct public/client PostgREST access;
--      backend direct SQLAlchemy / service_role connection manages queries with
--      strict per-request role verification (ADMIN or SUPER_ADMIN).
--   3. Chronological Indexing: High-performance retrieval ordered by created_at.
--
-- Safe to re-run: Uses IF NOT EXISTS throughout.
-- Backward Compatible: YES
-- =============================================================================

-- ── 1. Admin Group Messages Table ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.admin_group_messages (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    sender_firebase_uid TEXT         NOT NULL,
    sender_email        TEXT         NOT NULL,
    sender_name         TEXT         NOT NULL,
    sender_role         VARCHAR(20)  NOT NULL CHECK (sender_role IN ('ADMIN', 'SUPER_ADMIN')),
    message             TEXT         NOT NULL CHECK (char_length(trim(message)) >= 1 AND char_length(message) <= 5000),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── 2. Indexes ───────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_admin_group_messages_created_at
    ON public.admin_group_messages (created_at ASC, id ASC);

CREATE INDEX IF NOT EXISTS idx_admin_group_messages_sender_uid
    ON public.admin_group_messages (sender_firebase_uid);

-- ── 3. Table Comments ────────────────────────────────────────────────────────
COMMENT ON TABLE public.admin_group_messages IS 'Dedicated shared group chat exclusively for authenticated Admins and Super Admins.';
COMMENT ON COLUMN public.admin_group_messages.sender_firebase_uid IS 'Firebase UID of authenticated admin sender.';
COMMENT ON COLUMN public.admin_group_messages.sender_email IS 'Email address of authenticated admin sender.';
COMMENT ON COLUMN public.admin_group_messages.sender_name IS 'Display name of admin sender derived on backend.';
COMMENT ON COLUMN public.admin_group_messages.sender_role IS 'Role of sender at message creation time (ADMIN or SUPER_ADMIN).';
COMMENT ON COLUMN public.admin_group_messages.message IS 'Message text content (1-5000 characters).';
COMMENT ON COLUMN public.admin_group_messages.created_at IS 'Server timestamp when message was inserted.';

-- ── 4. Row Level Security ────────────────────────────────────────────────────
ALTER TABLE public.admin_group_messages ENABLE ROW LEVEL SECURITY;

-- Block client-side PostgREST completely; backend direct SQLAlchemy connection manages queries
DROP POLICY IF EXISTS "admin_group_messages_deny_client" ON public.admin_group_messages;
CREATE POLICY "admin_group_messages_deny_client" ON public.admin_group_messages FOR ALL TO public USING (false);

