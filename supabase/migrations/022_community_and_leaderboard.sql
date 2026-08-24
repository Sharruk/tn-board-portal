-- =============================================================================
-- Migration 022 — Community Posts, Comments & Contributor Leaderboard
-- TN State Board Learning Platform
-- =============================================================================
-- Purpose:
--   1. Add community_posts table for platform discussions.
--   2. Add community_comments table for replies to discussion posts.
--   3. Add community_post_votes table to track upvotes per user.
--   4. Add appropriate indexes and RLS policies.
--
-- Safe to re-run: Uses IF NOT EXISTS throughout.
-- =============================================================================

-- ── 1. community_posts ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS community_posts (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid TEXT        NOT NULL,
    author_name TEXT         NOT NULL,
    title       VARCHAR(255) NOT NULL,
    content     TEXT         NOT NULL,
    upvotes     INTEGER      NOT NULL DEFAULT 0,
    is_pinned   BOOLEAN      NOT NULL DEFAULT false,
    is_deleted  BOOLEAN      NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_community_posts_created_at ON community_posts (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_posts_firebase_uid ON community_posts (firebase_uid);
CREATE INDEX IF NOT EXISTS idx_community_posts_is_deleted ON community_posts (is_deleted);

COMMENT ON TABLE community_posts IS 'Public community discussion posts.';
COMMENT ON COLUMN community_posts.firebase_uid IS 'Firebase UID of author (not exposed publicly).';
COMMENT ON COLUMN community_posts.author_name IS 'Display name of author shown publicly.';


-- ── 2. community_comments ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS community_comments (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id      UUID        NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    firebase_uid TEXT        NOT NULL,
    author_name  TEXT        NOT NULL,
    content      TEXT        NOT NULL,
    is_deleted   BOOLEAN     NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_community_comments_post_id ON community_comments (post_id);
CREATE INDEX IF NOT EXISTS idx_community_comments_created_at ON community_comments (created_at ASC);

COMMENT ON TABLE community_comments IS 'Comments/replies to community discussion posts.';


-- ── 3. community_post_votes ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS community_post_votes (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id      UUID        NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    firebase_uid TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_community_post_votes_post_user UNIQUE (post_id, firebase_uid)
);

CREATE INDEX IF NOT EXISTS idx_community_post_votes_post_id ON community_post_votes (post_id);


-- ── 4. RLS Configuration ─────────────────────────────────────────────────────

ALTER TABLE community_posts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE community_comments   ENABLE ROW LEVEL SECURITY;
ALTER TABLE community_post_votes ENABLE ROW LEVEL SECURITY;

-- Public can read non-deleted posts
DROP POLICY IF EXISTS "community_posts_public_read" ON community_posts;
CREATE POLICY "community_posts_public_read"
    ON community_posts
    FOR SELECT
    TO anon, authenticated
    USING (is_deleted = false);

-- Public can read non-deleted comments
DROP POLICY IF EXISTS "community_comments_public_read" ON community_comments;
CREATE POLICY "community_comments_public_read"
    ON community_comments
    FOR SELECT
    TO anon, authenticated
    USING (is_deleted = false);

-- Service role bypasses RLS for backend insertions/updates
