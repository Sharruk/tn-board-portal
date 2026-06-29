import { supabase } from '../lib/supabase'

// =============================================================================
// Official Notices — Public Service
// =============================================================================

// ── Constants ─────────────────────────────────────────────────────────────────

export const NOTICE_CATEGORIES = [
  'Monthly Test Timetable',
  'Unit Test Timetable',
  'Quarterly Timetable',
  'Half Yearly Timetable',
  'Annual Exam Timetable',
  'Public Exam Timetable',
  'Supplementary Timetable',
  'Practical Timetable',
  'Hall Ticket',
  'Results',
  'School Circular',
  'Government Circular',
  'Admissions',
  'Counselling',
  'Scholarships',
  'Recruitment',
  'Announcements',
  'Other',
]

export const CATEGORY_ICONS = {
  'Monthly Test Timetable': '🗓️',
  'Unit Test Timetable':    '📝',
  'Quarterly Timetable':    '📅',
  'Half Yearly Timetable':  '📅',
  'Annual Exam Timetable':  '📅',
  'Public Exam Timetable':  '📅',
  'Supplementary Timetable':'📅',
  'Practical Timetable':    '🔬',
  'Hall Ticket':            '🎫',
  'Results':                '🏆',
  'School Circular':        '📢',
  'Government Circular':    '🏛️',
  'Admissions':             '🎓',
  'Counselling':            '🧭',
  'Scholarships':           '💰',
  'Recruitment':            '👔',
  'Announcements':          '📣',
  'Other':                  '📄',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Given a filename/file_path, determine the preview strategy.
 *   'pdf'   → browser PDF viewer
 *   'image' → <img> preview
 *   'docx'  → Microsoft Office Online Viewer
 *   'xlsx'  → Microsoft Office Online Viewer
 *   'pptx'  → Microsoft Office Online Viewer
 *   'other' → download only
 */
export function getFileType(filename) {
  if (!filename) return 'other'
  const ext = filename.split('.').pop().toLowerCase()
  if (ext === 'pdf') return 'pdf'
  if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return 'image'
  if (['doc', 'docx'].includes(ext)) return 'docx'
  if (['xls', 'xlsx'].includes(ext)) return 'xlsx'
  if (['ppt', 'pptx'].includes(ext)) return 'pptx'
  return 'other'
}

/** Build Microsoft Office Online Viewer URL for Word/Excel/PowerPoint files. */
export function getOfficeViewerUrl(publicUrl) {
  return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(publicUrl)}`
}

/**
 * Extract the YouTube video ID from any supported YouTube URL.
 * Supports:
 *   https://youtu.be/<id>
 *   https://www.youtube.com/watch?v=<id>
 *   https://www.youtube.com/shorts/<id>
 * Returns the video ID string or null if not matched.
 */
export function extractYouTubeId(url) {
  if (!url) return null
  try {
    const parsed = new URL(url)
    const host = parsed.hostname.replace(/^www\./, '')
    if (host === 'youtu.be') {
      return parsed.pathname.slice(1) || null
    }
    if (host === 'youtube.com') {
      if (parsed.pathname.startsWith('/shorts/')) {
        return parsed.pathname.replace('/shorts/', '') || null
      }
      return parsed.searchParams.get('v') || null
    }
  } catch {
    return null
  }
  return null
}

/**
 * Returns true if the URL is a valid YouTube link we support.
 */
export function isValidYouTubeUrl(url) {
  if (!url || !url.trim()) return true // blank is fine (optional field)
  return extractYouTubeId(url) !== null
}

/**
 * Build the embed URL for a YouTube video/Shorts.
 * Returns null if the input URL is not a recognised YouTube link.
 */
export function getYouTubeEmbedUrl(url) {
  const id = extractYouTubeId(url)
  if (!id) return null
  return `https://www.youtube.com/embed/${id}`
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Fetch the most recent visible, non-expired notices.  */
export const getRecentNotices = async (limit = 10) => {
  const { data, error } = await supabase
    .from('official_notices')
    .select('*, classes(name)')
    .eq('is_visible', true)
    .or(`expires_at.is.null,expires_at.gt.${new Date().toISOString()}`)
    .order('is_pinned', { ascending: false })
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return {
    data: data.map(n => ({
      ...n,
      class_name: n.classes?.name ?? null,
    })),
  }
}

/** Fetch a single notice by id (public view — only visible, non-expired). */
export const getNotice = async (id) => {
  const { data, error } = await supabase
    .from('official_notices')
    .select('*, classes(name)')
    .eq('id', id)
    .eq('is_visible', true)
    .single()
  if (error) throw error
  return {
    data: {
      ...data,
      class_name: data.classes?.name ?? null,
    },
  }
}

/** Fetch a single notice by id with NO visibility filter (for admin use). */
export const getNoticeAdmin = async (id) => {
  const { data, error } = await supabase
    .from('official_notices')
    .select('*, classes(name)')
    .eq('id', id)
    .single()
  if (error) throw error
  return {
    data: {
      ...data,
      class_name: data.classes?.name ?? null,
    },
  }
}

/** Fetch related notices in the same category (excluding the current notice). */
export const getRelatedNotices = async (category, excludeId, limit = 4) => {
  const { data, error } = await supabase
    .from('official_notices')
    .select('*, classes(name)')
    .eq('category', category)
    .eq('is_visible', true)
    .neq('id', excludeId)
    .or(`expires_at.is.null,expires_at.gt.${new Date().toISOString()}`)
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return {
    data: data.map(n => ({
      ...n,
      class_name: n.classes?.name ?? null,
    })),
  }
}

/** Increment view count. Fire-and-forget; errors are silently ignored. */
export const recordNoticeView = (id) =>
  supabase.rpc('record_notice_view', { p_id: id }).then(() => {}).catch(() => {})

/** Increment download count. Fire-and-forget; errors are silently ignored. */
export const recordNoticeDownload = (id) =>
  supabase.rpc('record_notice_download', { p_id: id }).then(() => {}).catch(() => {})
