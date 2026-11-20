-- =============================================================================
-- Migration 035 — Study Material Interactions (Likes & Threaded Comments)
-- TN State Board Student Portal — Hungry Learner
-- =============================================================================

-- ── 1. study_material_likes Table ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS study_material_likes (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id  UUID        NOT NULL REFERENCES study_materials(id) ON DELETE CASCADE,
    firebase_uid TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_study_material_likes_user UNIQUE (material_id, firebase_uid)
);

CREATE INDEX IF NOT EXISTS idx_study_material_likes_material_id ON study_material_likes (material_id);
CREATE INDEX IF NOT EXISTS idx_study_material_likes_firebase_uid ON study_material_likes (firebase_uid);

COMMENT ON TABLE study_material_likes IS 'Authenticated student likes on study materials.';


-- ── 2. study_material_comments Table ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS study_material_comments (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id   UUID        NOT NULL REFERENCES study_materials(id) ON DELETE CASCADE,
    firebase_uid  TEXT        NOT NULL,
    author_name   TEXT        NOT NULL,
    author_avatar TEXT        NULL,
    parent_id     UUID        NULL REFERENCES study_material_comments(id) ON DELETE CASCADE,
    content       TEXT        NOT NULL,
    is_deleted    BOOLEAN     NOT NULL DEFAULT false,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_study_material_comments_material_id ON study_material_comments (material_id);
CREATE INDEX IF NOT EXISTS idx_study_material_comments_parent_id ON study_material_comments (parent_id);
CREATE INDEX IF NOT EXISTS idx_study_material_comments_created_at ON study_material_comments (created_at ASC);

COMMENT ON TABLE study_material_comments IS 'Discussion comments and replies on study material detail pages.';


-- ── 3. Row Level Security & Policies ────────────────────────────────────────
ALTER TABLE study_material_likes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_material_comments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "study_material_likes_public_read" ON study_material_likes;
CREATE POLICY "study_material_likes_public_read"
    ON study_material_likes
    FOR SELECT
    TO anon, authenticated
    USING (true);

DROP POLICY IF EXISTS "study_material_likes_auth_insert" ON study_material_likes;
CREATE POLICY "study_material_likes_auth_insert"
    ON study_material_likes
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

DROP POLICY IF EXISTS "study_material_likes_auth_delete" ON study_material_likes;
CREATE POLICY "study_material_likes_auth_delete"
    ON study_material_likes
    FOR DELETE
    TO authenticated
    USING (true);

DROP POLICY IF EXISTS "study_material_comments_public_read" ON study_material_comments;
CREATE POLICY "study_material_comments_public_read"
    ON study_material_comments
    FOR SELECT
    TO anon, authenticated
    USING (is_deleted = false);

DROP POLICY IF EXISTS "study_material_comments_auth_insert" ON study_material_comments;
CREATE POLICY "study_material_comments_auth_insert"
    ON study_material_comments
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

DROP POLICY IF EXISTS "study_material_comments_auth_update" ON study_material_comments;
CREATE POLICY "study_material_comments_auth_update"
    ON study_material_comments
    FOR UPDATE
    TO authenticated
    USING (true);
