-- =============================================================================
-- Migration 023 — Analytics Events, Community Enhancements, Paper Interactions,
--                  Paper Requests & Content Moderation Reports
-- TN State Board Learning Platform
-- =============================================================================
-- Safe to re-run: Uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS throughout.
-- =============================================================================

-- ── 1. analytics_events Table ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analytics_events (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type   VARCHAR(50)  NOT NULL, -- 'page_view', 'paper_view', 'download', 'search', 'like', 'comment'
    session_id   VARCHAR(100) NULL,     -- Anonymous session identifier
    firebase_uid TEXT         NULL,     -- Optional authenticated user identifier
    paper_id     INTEGER      NULL REFERENCES papers(id) ON DELETE SET NULL,
    class_id     INTEGER      NULL REFERENCES classes(id) ON DELETE SET NULL,
    subject_id   INTEGER      NULL REFERENCES subjects(id) ON DELETE SET NULL,
    metadata     JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events (event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_paper_id ON analytics_events (paper_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_class_id ON analytics_events (class_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_subject_id ON analytics_events (subject_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events (session_id);

COMMENT ON TABLE analytics_events IS 'Privacy-conscious analytics and usage telemetry events.';


-- ── 2. community_posts Enhancements ──────────────────────────────────────────
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'Discussion';
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS author_avatar TEXT NULL;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'open'; -- 'open', 'resolved', 'closed'
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS likes_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS comments_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_community_posts_category ON community_posts (category);
CREATE INDEX IF NOT EXISTS idx_community_posts_status ON community_posts (status);


-- ── 3. community_comments Enhancements ────────────────────────────────────────
ALTER TABLE community_comments ADD COLUMN IF NOT EXISTS parent_id UUID NULL REFERENCES community_comments(id) ON DELETE CASCADE;
ALTER TABLE community_comments ADD COLUMN IF NOT EXISTS author_avatar TEXT NULL;

CREATE INDEX IF NOT EXISTS idx_community_comments_parent_id ON community_comments (parent_id);


-- ── 4. paper_likes Table ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paper_likes (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id     INTEGER     NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    firebase_uid TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_paper_likes_paper_user UNIQUE (paper_id, firebase_uid)
);

CREATE INDEX IF NOT EXISTS idx_paper_likes_paper_id ON paper_likes (paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_likes_firebase_uid ON paper_likes (firebase_uid);

COMMENT ON TABLE paper_likes IS 'Authenticated user likes on question papers.';


-- ── 5. paper_comments Table ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paper_comments (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    paper_id      INTEGER     NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    firebase_uid  TEXT        NOT NULL,
    author_name   TEXT        NOT NULL,
    author_avatar TEXT        NULL,
    parent_id     UUID        NULL REFERENCES paper_comments(id) ON DELETE CASCADE,
    content       TEXT        NOT NULL,
    is_deleted    BOOLEAN     NOT NULL DEFAULT false,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_comments_paper_id ON paper_comments (paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_comments_parent_id ON paper_comments (parent_id);
CREATE INDEX IF NOT EXISTS idx_paper_comments_created_at ON paper_comments (created_at ASC);

COMMENT ON TABLE paper_comments IS 'Discussion comments and replies on paper detail pages.';


-- ── 6. paper_requests Table ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS paper_requests (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    firebase_uid        TEXT         NOT NULL,
    author_name         TEXT         NOT NULL,
    author_avatar       TEXT         NULL,
    class_id            INTEGER      NULL REFERENCES classes(id) ON DELETE SET NULL,
    subject_id          INTEGER      NULL REFERENCES subjects(id) ON DELETE SET NULL,
    exam_type           VARCHAR(100) NOT NULL,
    year                INTEGER      NOT NULL,
    month               VARCHAR(50)  NULL,
    district            VARCHAR(100) NULL,
    title               VARCHAR(255) NOT NULL,
    description         TEXT         NULL,
    status              VARCHAR(30)  NOT NULL DEFAULT 'open', -- 'open', 'in_progress', 'fulfilled', 'closed'
    fulfilled_paper_id  INTEGER      NULL REFERENCES papers(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_paper_requests_created_at ON paper_requests (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_paper_requests_status ON paper_requests (status);
CREATE INDEX IF NOT EXISTS idx_paper_requests_firebase_uid ON paper_requests (firebase_uid);

COMMENT ON TABLE paper_requests IS 'Community requests for missing examination papers.';


-- ── 7. content_reports Table ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content_reports (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_uid TEXT         NOT NULL,
    target_type  VARCHAR(30)  NOT NULL, -- 'post', 'comment', 'paper_comment', 'request'
    target_id    VARCHAR(100) NOT NULL,
    reason       TEXT         NOT NULL,
    status       VARCHAR(30)  NOT NULL DEFAULT 'pending', -- 'pending', 'reviewed', 'dismissed', 'actioned'
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_content_reports_created_at ON content_reports (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_reports_status ON content_reports (status);

COMMENT ON TABLE content_reports IS 'User reports for inappropriate community content.';


-- ── 8. Row Level Security & Policies ──────────────────────────────────────────
ALTER TABLE analytics_events  ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_likes       ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_comments    ENABLE ROW LEVEL SECURITY;
ALTER TABLE paper_requests    ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_reports   ENABLE ROW LEVEL SECURITY;

-- Analytics: anyone can insert events (via public anon role or backend)
DROP POLICY IF EXISTS "analytics_events_insert_all" ON analytics_events;
CREATE POLICY "analytics_events_insert_all"
    ON analytics_events
    FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- Paper likes: public can view counts/likes
DROP POLICY IF EXISTS "paper_likes_public_read" ON paper_likes;
CREATE POLICY "paper_likes_public_read"
    ON paper_likes
    FOR SELECT
    TO anon, authenticated
    USING (true);

-- Paper comments: public can view non-deleted comments
DROP POLICY IF EXISTS "paper_comments_public_read" ON paper_comments;
CREATE POLICY "paper_comments_public_read"
    ON paper_comments
    FOR SELECT
    TO anon, authenticated
    USING (is_deleted = false);

-- Paper requests: public can read all requests
DROP POLICY IF EXISTS "paper_requests_public_read" ON paper_requests;
CREATE POLICY "paper_requests_public_read"
    ON paper_requests
    FOR SELECT
    TO anon, authenticated
    USING (true);
