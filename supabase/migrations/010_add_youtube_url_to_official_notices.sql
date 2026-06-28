-- =============================================================================
-- Migration 010 — Add youtube_url to official_notices
-- TN State Board Student Portal
-- =============================================================================
-- Adds an optional youtube_url column to official_notices so that admins can
-- attach a YouTube video (normal video or Shorts) to any notice.
--
-- Design goals:
--   • Fully backward-compatible: existing rows are not touched (NULL default)
--   • No changes to Question Papers, existing notices, routes, or uploads
--   • Simple TEXT column — URL validation is done in the frontend
-- =============================================================================

ALTER TABLE official_notices
  ADD COLUMN IF NOT EXISTS youtube_url TEXT DEFAULT NULL;

COMMENT ON COLUMN official_notices.youtube_url IS
  'Optional YouTube video or Shorts URL attached to this notice. '
  'Accepted formats: https://youtu.be/..., https://www.youtube.com/watch?v=..., '
  'https://www.youtube.com/shorts/... — NULL means no video.';
