-- =============================================================================
-- Migration 011 — News & Updates
-- TN State Board Student Portal
-- =============================================================================
-- Creates the news_updates table for daily education news, holiday
-- announcements, government updates, exam updates, counselling news, etc.
--
-- Design goals:
--   • Completely separate from official_notices and papers tables
--   • UUID primary key (consistent with Supabase best practices)
--   • Slug for clean URLs  (/news/:slug)
--   • Status enum: draft | published | archived
--   • Optional thumbnail, PDF, YouTube, class/district association
--   • ILIKE search RPC following existing search_notices() pattern
--   • Fire-and-forget view counter RPC
--
-- Storage: files go in the separate "news-media" bucket
-- =============================================================================

-- ── news_updates ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS news_updates (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(400)    NOT NULL,
    slug            VARCHAR(500)    NOT NULL UNIQUE,
    summary         TEXT,
    content         TEXT,
    category        VARCHAR(100)    NOT NULL,
    tags            TEXT[]          DEFAULT '{}',
    thumbnail_url   TEXT,
    thumbnail_alt   VARCHAR(300),
    youtube_url     TEXT,
    pdf_url         TEXT,
    class_id        INTEGER         REFERENCES classes(id) ON DELETE SET NULL,
    district        VARCHAR(150),
    status          VARCHAR(20)     NOT NULL DEFAULT 'draft'
                                    CHECK (status IN ('draft', 'published', 'archived')),
    is_pinned       BOOLEAN         NOT NULL DEFAULT false,
    view_count      INTEGER         NOT NULL DEFAULT 0,
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_news_slug         ON news_updates (slug);
CREATE INDEX IF NOT EXISTS idx_news_category     ON news_updates (category);
CREATE INDEX IF NOT EXISTS idx_news_status       ON news_updates (status);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_updates (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_is_pinned    ON news_updates (is_pinned);
CREATE INDEX IF NOT EXISTS idx_news_class_id     ON news_updates (class_id);
CREATE INDEX IF NOT EXISTS idx_news_district     ON news_updates (district);
CREATE INDEX IF NOT EXISTS idx_news_created_at   ON news_updates (created_at DESC);

-- ── Comments ──────────────────────────────────────────────────────────────────

COMMENT ON TABLE  news_updates IS
  'Daily education news, holiday announcements, government updates, exam changes, counselling news, etc.';
COMMENT ON COLUMN news_updates.slug IS
  'URL-safe slug derived from title. Used for clean URLs: /news/:slug.';
COMMENT ON COLUMN news_updates.status IS
  'draft = not visible to public; published = visible if published_at <= NOW(); archived = hidden.';
COMMENT ON COLUMN news_updates.is_pinned IS
  'Pinned articles appear at the top of listings and the home page section.';
COMMENT ON COLUMN news_updates.view_count IS
  'Incremented on each public detail page load via increment_news_views() RPC.';

-- ── updated_at trigger ───────────────────────────────────────────────────────
-- Reuse the function defined in migration 008 (set_updated_at) if it exists.

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_news_updated_at ON news_updates;
CREATE TRIGGER trg_news_updated_at
    BEFORE UPDATE ON news_updates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── RLS ───────────────────────────────────────────────────────────────────────

ALTER TABLE news_updates ENABLE ROW LEVEL SECURITY;

-- Public: only published articles with published_at <= NOW()
CREATE POLICY "news_public_select" ON news_updates
    FOR SELECT
    TO anon, authenticated
    USING (
        status = 'published'
        AND (published_at IS NULL OR published_at <= NOW())
    );

-- Admin: full access
CREATE POLICY "news_admin_all" ON news_updates
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- ── View counter RPC ──────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION increment_news_views(p_id UUID)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    UPDATE news_updates SET view_count = view_count + 1 WHERE id = p_id;
END;
$$;

GRANT EXECUTE ON FUNCTION increment_news_views(UUID) TO anon;
GRANT EXECUTE ON FUNCTION increment_news_views(UUID) TO authenticated;

-- ── Search RPC ────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION search_news(
    q          TEXT,
    p_category TEXT    DEFAULT NULL,
    p_limit    INTEGER DEFAULT 50
)
RETURNS TABLE (
    id            UUID,
    title         TEXT,
    slug          TEXT,
    summary       TEXT,
    category      TEXT,
    thumbnail_url TEXT,
    youtube_url   TEXT,
    is_pinned     BOOLEAN,
    view_count    INTEGER,
    published_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.id,
        n.title::TEXT,
        n.slug::TEXT,
        n.summary::TEXT,
        n.category::TEXT,
        n.thumbnail_url::TEXT,
        n.youtube_url::TEXT,
        n.is_pinned,
        n.view_count,
        n.published_at,
        n.created_at
    FROM   news_updates n
    WHERE  n.status = 'published'
      AND  (n.published_at IS NULL OR n.published_at <= NOW())
      AND  (
               n.title    ILIKE '%' || q || '%'
            OR n.summary  ILIKE '%' || q || '%'
            OR n.category ILIKE '%' || q || '%'
            OR n.content  ILIKE '%' || q || '%'
           )
      AND  (p_category IS NULL OR n.category = p_category)
    ORDER BY n.is_pinned DESC, n.published_at DESC NULLS LAST
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION search_news(TEXT, TEXT, INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION search_news(TEXT, TEXT, INTEGER) TO authenticated;

COMMENT ON FUNCTION search_news IS
  'ILIKE search over news_updates. Priority: title > summary > category > content. '
  'Returns only published articles with published_at <= NOW(). Pinned first.';

-- ── Supabase Storage bucket ───────────────────────────────────────────────────
-- Run in Supabase Dashboard → Storage if bucket does not exist.
-- The INSERT is idempotent (ON CONFLICT DO NOTHING).

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'news-media',
    'news-media',
    true,
    20971520,   -- 20 MB limit
    ARRAY[
        'image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif',
        'application/pdf'
    ]
)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS: public read
CREATE POLICY "news_media_public_read"
    ON storage.objects FOR SELECT
    TO public
    USING (bucket_id = 'news-media');

-- Storage RLS: authenticated upload
CREATE POLICY "news_media_admin_insert"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (bucket_id = 'news-media');

-- Storage RLS: authenticated update
CREATE POLICY "news_media_admin_update"
    ON storage.objects FOR UPDATE
    TO authenticated
    USING (bucket_id = 'news-media');

-- Storage RLS: authenticated delete
CREATE POLICY "news_media_admin_delete"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (bucket_id = 'news-media');
