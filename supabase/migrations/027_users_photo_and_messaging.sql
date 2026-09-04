-- =============================================================================
-- Migration 027 — User Profile Photo, Activity Tracking & Student-Admin Messaging
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   1. Add `photo_url` and `last_active_at` to `users` table.
--   2. Add `conversations` table for student-to-admin support / material inquiries.
--   3. Add `messages` table for individual message items inside a conversation.
--   4. Add indexes and comments for high performance and clarity.
--
-- Safe to re-run: Uses IF NOT EXISTS throughout.
-- =============================================================================

-- ── 1. Users Table Enhancements ──────────────────────────────────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS photo_url TEXT,
    ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ DEFAULT NOW();

COMMENT ON COLUMN users.photo_url IS 'Authenticated user Google profile photo URL (lh3.googleusercontent.com).';
COMMENT ON COLUMN users.last_active_at IS 'Timestamp of user''s latest authenticated activity.';

-- ── 2. Conversations Table ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conversations (
    id                 UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid       TEXT         NOT NULL,
    user_email         TEXT         NOT NULL,
    user_display_name  TEXT         NOT NULL,
    category           VARCHAR(50)  NOT NULL, -- 'general_question', 'material_request', 'submission_status', 'report_problem', 'feedback', 'other'
    subject            VARCHAR(255) NOT NULL,
    status             VARCHAR(50)  NOT NULL DEFAULT 'awaiting_admin', -- 'open', 'awaiting_admin', 'awaiting_user', 'resolved'
    submission_id      UUID         NULL REFERENCES submissions(id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_firebase_uid ON conversations (firebase_uid);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations (status);
CREATE INDEX IF NOT EXISTS idx_conversations_category ON conversations (category);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_submission_id ON conversations (submission_id);

COMMENT ON TABLE conversations IS 'Student support, material requests, and submission inquiries with TN Board Admin.';
COMMENT ON COLUMN conversations.firebase_uid IS 'Firebase UID of student owner.';
COMMENT ON COLUMN conversations.category IS 'Inquiry category (general_question, material_request, submission_status, etc.)';
COMMENT ON COLUMN conversations.status IS 'Current conversation lifecycle status.';
COMMENT ON COLUMN conversations.submission_id IS 'Optional reference to user submission if asking about a specific submission.';

-- ── 3. Messages Table ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_role         VARCHAR(20) NOT NULL, -- 'user' or 'admin'
    sender_firebase_uid TEXT        NOT NULL,
    sender_name         TEXT        NOT NULL,
    message             TEXT        NOT NULL,
    is_read             BOOLEAN     NOT NULL DEFAULT false,
    read_at             TIMESTAMPTZ NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages (created_at ASC);
CREATE INDEX IF NOT EXISTS idx_messages_unread ON messages (conversation_id, sender_role, is_read);

COMMENT ON TABLE messages IS 'Individual messages within a student-admin conversation thread.';

-- ── 4. Row Level Security ────────────────────────────────────────────────────
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Backend uses direct connection / service_role to manage all reads and writes.
