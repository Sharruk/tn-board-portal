-- =============================================================================
-- Migration 008 — Official Notices
-- TN State Board Student Portal
-- =============================================================================
-- Creates the official_notices table for timetables, circulars, notifications,
-- government orders, and all other official education documents.
--
-- Design goals:
--   • Completely separate from the papers table — does not touch existing data
--   • Supports pin/unpin, optional expiry, view/download counters
--   • Optional class association (some notices are class-specific)
--   • Search via ILIKE RPC to match patterns used by search_papers()
--
-- Storage: files go in the separate "official-updates" bucket (not "papers")
-- =============================================================================

-- ── official_notices ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS official_notices (
    id              SERIAL          PRIMARY KEY,
    title           VARCHAR(300)    NOT NULL,
    category        VARCHAR(100)    NOT NULL,   -- see NOTICE_CATEGORIES in frontend
    class_id        INTEGER         REFERENCES classes(id) ON DELETE SET NULL,  -- nullable
    year            INTEGER         NOT NULL,
    description     TEXT,                       -- optional rich description
    file_path       VARCHAR(500),               -- Supabase Storage object key
    public_url      TEXT,                       -- Supabase Storage public CDN URL
    file_type       VARCHAR(20),                -- 'pdf' | 'image' | 'docx' | 'xlsx' | 'pptx' | 'other'
    is_visible      BOOLEAN         NOT NULL DEFAULT false,
    is_pinned       BOOLEAN         NOT NULL DEFAULT false,
    expires_at      TIMESTAMPTZ,                -- NULL means never expires
    view_count      INTEGER         NOT NULL DEFAULT 0,
    download_count  INTEGER         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notices_category    ON official_notices (category);
CREATE INDEX IF NOT EXISTS idx_notices_class_id    ON official_notices (class_id);
CREATE INDEX IF NOT EXISTS idx_notices_year        ON official_notices (year);
CREATE INDEX IF NOT EXISTS idx_notices_is_visible  ON official_notices (is_visible);
CREATE INDEX IF NOT EXISTS idx_notices_is_pinned   ON official_notices (is_pinned);
CREATE INDEX IF NOT EXISTS idx_notices_expires_at  ON official_notices (expires_at);
CREATE INDEX IF NOT EXISTS idx_notices_created_at  ON official_notices (created_at DESC);

COMMENT ON TABLE  official_notices               IS 'Official education notices: timetables, circulars, results, government orders, etc.';
COMMENT ON COLUMN official_notices.category      IS 'Predefined category from NOTICE_CATEGORIES constant in the frontend.';
COMMENT ON COLUMN official_notices.class_id      IS 'NULL = applies to all classes; set for class-specific notices.';
COMMENT ON COLUMN official_notices.file_type     IS 'Determines preview strategy: pdf|image→browser, docx|xlsx|pptx→Office Online, other→download only.';
COMMENT ON COLUMN official_notices.is_pinned     IS 'Pinned notices appear at top of listing and in the featured banner on the home page.';
COMMENT ON COLUMN official_notices.expires_at    IS 'If set and past current time, notice is hidden from public view (admin still sees it).';
COMMENT ON COLUMN official_notices.view_count    IS 'Incremented on each public detail page load via record_notice_view() RPC.';
COMMENT ON COLUMN official_notices.download_count IS 'Incremented on each download via record_notice_download() RPC.';


-- ── updated_at trigger ───────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_notices_updated_at ON official_notices;
CREATE TRIGGER trg_notices_updated_at
    BEFORE UPDATE ON official_notices
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ── RLS policies ──────────────────────────────────────────────────────────────

ALTER TABLE official_notices ENABLE ROW LEVEL SECURITY;

-- Public: only visible, non-expired notices
CREATE POLICY "notices_public_select" ON official_notices
    FOR SELECT
    TO anon, authenticated
    USING (
        is_visible = true
        AND (expires_at IS NULL OR expires_at > NOW())
    );

-- Admin: full access (authenticated users can see ALL rows for management)
CREATE POLICY "notices_admin_all" ON official_notices
    FOR ALL
    TO authenticated
    USING (true)
    WITH CHECK (true);


-- ── Counters ─────────────────────────────────────────────────────────────────

-- Safely increments view_count. Called from the public detail page.
CREATE OR REPLACE FUNCTION record_notice_view(p_id INTEGER)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    UPDATE official_notices SET view_count = view_count + 1 WHERE id = p_id;
END;
$$;

GRANT EXECUTE ON FUNCTION record_notice_view(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION record_notice_view(INTEGER) TO authenticated;

-- Safely increments download_count. Called from the public detail page on download.
CREATE OR REPLACE FUNCTION record_notice_download(p_id INTEGER)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    UPDATE official_notices SET download_count = download_count + 1 WHERE id = p_id;
END;
$$;

GRANT EXECUTE ON FUNCTION record_notice_download(INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION record_notice_download(INTEGER) TO authenticated;


-- ── Search RPC ───────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION search_notices(
    q             TEXT,
    p_category    TEXT    DEFAULT NULL,
    p_class_id    INTEGER DEFAULT NULL,
    p_year        INTEGER DEFAULT NULL
)
RETURNS TABLE (
    id             INTEGER,
    title          TEXT,
    category       TEXT,
    class_id       INTEGER,
    class_name     TEXT,
    year           INTEGER,
    description    TEXT,
    public_url     TEXT,
    file_type      TEXT,
    is_pinned      BOOLEAN,
    view_count     INTEGER,
    download_count INTEGER,
    created_at     TIMESTAMPTZ
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
        n.category::TEXT,
        n.class_id,
        c.name::TEXT AS class_name,
        n.year,
        n.description::TEXT,
        n.public_url::TEXT,
        n.file_type::TEXT,
        n.is_pinned,
        n.view_count,
        n.download_count,
        n.created_at
    FROM   official_notices n
    LEFT JOIN classes c ON c.id = n.class_id
    WHERE  n.is_visible = true
      AND  (n.expires_at IS NULL OR n.expires_at > NOW())
      AND  (
               n.title       ILIKE '%' || q || '%'
            OR n.category    ILIKE '%' || q || '%'
            OR n.description ILIKE '%' || q || '%'
            OR (c.name IS NOT NULL AND c.name ILIKE '%' || q || '%')
           )
      AND  (p_category IS NULL OR n.category = p_category)
      AND  (p_class_id IS NULL OR n.class_id = p_class_id)
      AND  (p_year     IS NULL OR n.year     = p_year)
    ORDER BY n.is_pinned DESC, n.created_at DESC
    LIMIT 50;
END;
$$;

GRANT EXECUTE ON FUNCTION search_notices(TEXT, TEXT, INTEGER, INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION search_notices(TEXT, TEXT, INTEGER, INTEGER) TO authenticated;

COMMENT ON FUNCTION search_notices IS
'Full-text ILIKE search over official_notices. Filters by category, class, and year. '
'Returns only visible, non-expired rows. Pinned notices are ranked first. '
'Called from frontend services/search.js via supabase.rpc().';


-- ── Supabase Storage bucket ───────────────────────────────────────────────────
-- NOTE: Run this block manually in the Supabase Dashboard → Storage if the bucket
-- does not yet exist. The INSERT below is idempotent (ON CONFLICT DO NOTHING).
-- Bucket: official-updates  |  Public: true  |  Allowed MIME types: open

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'official-updates',
    'official-updates',
    true,
    52428800,   -- 50 MB limit
    NULL        -- all MIME types allowed (PDF, images, DOCX, XLSX, PPTX, etc.)
)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS: public download
CREATE POLICY "official_updates_public_read"
    ON storage.objects FOR SELECT
    TO public
    USING (bucket_id = 'official-updates');

-- Storage RLS: authenticated upload / delete
CREATE POLICY "official_updates_admin_write"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (bucket_id = 'official-updates');

CREATE POLICY "official_updates_admin_delete"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (bucket_id = 'official-updates');
