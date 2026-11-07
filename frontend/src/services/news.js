import { supabase } from '../lib/supabase'
import { getFirebaseToken } from '../lib/firebase'
import { apiFetch, getApiUrl } from '../lib/api'

// =============================================================================
// News & Updates — Public + Admin Service
// =============================================================================

// ── Constants ─────────────────────────────────────────────────────────────────

export const NEWS_CATEGORIES = [
  'Breaking News',
  'Exam Updates',
  'Result Announcements',
  'Timetable Updates',
  'Holiday Announcement',
  'District Holiday',
  'School Circular',
  'Government Update',
  'Admissions',
  'TNEA Counselling',
  'Scholarships',
  'Recruitment',
  'Textbook & Syllabus',
  'Skill Development',
  'Sports & Events',
  'Other',
]

export const NEWS_CATEGORY_ICONS = {
  'Breaking News':       '🔴',
  'Exam Updates':        '📝',
  'Result Announcements':'🏆',
  'Timetable Updates':   '📅',
  'Holiday Announcement':'🎉',
  'District Holiday':    '🏫',
  'School Circular':     '📢',
  'Government Update':   '🏛️',
  'Admissions':          '🎓',
  'TNEA Counselling':    '🧭',
  'Scholarships':        '💰',
  'Recruitment':         '👔',
  'Textbook & Syllabus': '📚',
  'Skill Development':   '🛠️',
  'Sports & Events':     '🏅',
  'Other':               '📰',
}

export const NEWS_STATUS_LABELS = {
  draft:     { label: 'Draft',     color: 'bg-gray-100 text-gray-600'    },
  published: { label: 'Published', color: 'bg-emerald-100 text-emerald-700' },
  archived:  { label: 'Archived',  color: 'bg-red-100 text-red-600'      },
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Generate a URL-safe slug from a title.
 * e.g. "Heavy Rain Holiday — Chennai" → "heavy-rain-holiday-chennai"
 */
export function generateSlug(title) {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')   // remove special chars (keep word chars, spaces, hyphens)
    .replace(/[\s_]+/g, '-')    // spaces/underscores → hyphens
    .replace(/-+/g, '-')        // collapse consecutive hyphens
    .replace(/^-+|-+$/g, '')    // trim leading/trailing hyphens
    .slice(0, 120)              // max length
}

/**
 * Format a published_at date for display.
 */
export function formatPublishedDate(dateStr, opts = {}) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day:   '2-digit',
    month: opts.short ? 'short' : 'long',
    year:  'numeric',
    ...opts,
  })
}

/**
 * Returns true if the article is visible to the public
 * (status = published AND published_at <= now).
 */
export function isNewsPublic(article) {
  if (!article) return false
  if (article.status !== 'published') return false
  if (article.published_at && new Date(article.published_at) > new Date()) return false
  return true
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Fetch the most recent published news articles (pinned first, then newest).
 */
export const getRecentNews = async (limit = 6) => {
  const { data, error } = await supabase
    .from('news_updates')
    .select('*, classes(name)')
    .eq('status', 'published')
    .lte('published_at', new Date().toISOString())
    .order('is_pinned', { ascending: false })
    .order('published_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return {
    data: data.map(n => ({ ...n, class_name: n.classes?.name ?? null })),
  }
}

/**
 * Fetch all published news articles with optional category filter.
 * Used by the public NewsPage listing.
 */
export const getAllNews = async ({ category = null, limit = 50, offset = 0 } = {}) => {
  let query = supabase
    .from('news_updates')
    .select('*, classes(name)', { count: 'exact' })
    .eq('status', 'published')
    .lte('published_at', new Date().toISOString())
    .order('is_pinned', { ascending: false })
    .order('published_at', { ascending: false })
    .range(offset, offset + limit - 1)

  if (category) query = query.eq('category', category)

  const { data, error, count } = await query
  if (error) throw error
  return {
    data: data.map(n => ({ ...n, class_name: n.classes?.name ?? null })),
    count: count ?? 0,
  }
}

/**
 * Fetch a single published article by slug (public view).
 */
export const getNewsBySlug = async (slug) => {
  const { data, error } = await supabase
    .from('news_updates')
    .select('*, classes(name)')
    .eq('slug', slug)
    .eq('status', 'published')
    .single()
  if (error) throw error
  return {
    data: { ...data, class_name: data.classes?.name ?? null },
  }
}

/**
 * Fetch a single article by id with no visibility filter (for admin use).
 * Strictly routes through FastAPI backend with Firebase Bearer token.
 */
export const getNewsAdmin = async (id) => {
  const token = await getFirebaseToken()
  try {
    const data = await apiFetch(`/api/v1/news/${id}`, {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })
    return {
      data: { ...data, class_name: data.class_name ?? null }
    }
  } catch (err) {
    throw new Error(`Failed to load article details from backend: ${err.message || err}`)
  }
}

/**
 * Fetch related articles in the same category (excluding current article).
 */
export const getRelatedNews = async (category, excludeId, limit = 4) => {
  const { data, error } = await supabase
    .from('news_updates')
    .select('*, classes(name)')
    .eq('category', category)
    .eq('status', 'published')
    .lte('published_at', new Date().toISOString())
    .neq('id', excludeId)
    .order('published_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return {
    data: data.map(n => ({ ...n, class_name: n.classes?.name ?? null })),
  }
}

/**
 * Increment view count. Fire-and-forget; errors are silently ignored.
 */
export const recordNewsView = (id) =>
  supabase.rpc('increment_news_views', { p_id: id }).then(() => {}).catch(() => {})

// ── Admin API ─────────────────────────────────────────────────────────────────

/**
 * Fetch ALL news articles for the admin table (no visibility filter).
 * Strictly routes through FastAPI backend with Firebase Bearer token.
 */
export const getAdminNews = async () => {
  const token = await getFirebaseToken()
  try {
    const res = await apiFetch('/api/v1/news/admin?limit=200', {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })
    const items = res?.data || []
    return {
      data: items.map(n => ({
        ...n,
        class_name: n.class_name ?? null,
      }))
    }
  } catch (err) {
    throw new Error(`Failed to load news articles from backend: ${err.message || err}`)
  }
}

/**
 * Archive a news article via backend API.
 */
export const archiveNews = async (id) => {
  const token = await getFirebaseToken()
  const data = await apiFetch(`/api/v1/news/${id}/archive`, {
    method: 'POST',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  })
  return { data }
}

/**
 * Unarchive / restore a news article to published status via backend API.
 */
export const unarchiveNews = async (id) => {
  const token = await getFirebaseToken()
  const data = await apiFetch(`/api/v1/news/${id}/unarchive`, {
    method: 'POST',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  })
  return { data }
}

/**
 * Create a new news article via backend API with centralized audit logging.
 */
export const createNews = async (payload) => {
  const token = await getFirebaseToken()
  const data = await apiFetch('/api/v1/news', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
  return { data }
}

/**
 * Update an existing news article via backend API with centralized audit logging.
 */
export const updateNews = async (id, updates) => {
  const token = await getFirebaseToken()
  const data = await apiFetch(`/api/v1/news/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(updates),
  })
  return { data }
}

/**
 * Delete a news article via backend API with transactional outbox storage cleanup.
 */
export const deleteNews = async (id) => {
  const token = await getFirebaseToken()
  return await apiFetch(`/api/v1/news/${id}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  })
}

/**
 * Upload a file (image or PDF) to the news-media bucket via FastAPI server-side storage client.
 * Returns { publicUrl, filename }.
 */
export const uploadNewsFile = async (file, onProgress) => {
  if (onProgress) onProgress(20)

  const token = await getFirebaseToken()
  const url = getApiUrl('/api/v1/news/upload')

  const fd = new FormData()
  fd.append('file', file)

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: fd,
  })

  if (onProgress) onProgress(80)

  if (!response.ok) {
    let detail = `Upload failed (HTTP ${response.status})`
    try {
      const errBody = await response.json()
      detail = errBody?.detail || errBody?.message || detail
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail)
  }

  const data = await response.json()
  if (onProgress) onProgress(100)

  return {
    publicUrl: data.public_url || data.publicUrl,
    filename: data.file_path || data.filename,
  }
}

/**
 * Delete a single file from the news-media bucket via the backend storage cleanup endpoint.
 * Errors are swallowed — used for cleanup when replacing images.
 */
export const deleteNewsFile = async (publicUrl) => {
  if (!publicUrl) return
  try {
    const token = await getFirebaseToken()
    const url = getApiUrl(`/api/v1/news/media?url=${encodeURIComponent(publicUrl)}`)
    await fetch(url, {
      method: 'DELETE',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    })
  } catch {
    // Non-fatal cleanup error
  }
}
