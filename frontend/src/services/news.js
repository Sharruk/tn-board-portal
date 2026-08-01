import { supabase } from '../lib/supabase'

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
 */
export const getNewsAdmin = async (id) => {
  const { data, error } = await supabase
    .from('news_updates')
    .select('*, classes(name)')
    .eq('id', id)
    .single()
  if (error) throw error
  return {
    data: { ...data, class_name: data.classes?.name ?? null },
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
 */
export const getAdminNews = async () => {
  const { data, error } = await supabase
    .from('news_updates')
    .select('*, classes(name)')
    .order('created_at', { ascending: false })
  if (error) throw error
  return {
    data: data.map(n => ({ ...n, class_name: n.classes?.name ?? null })),
  }
}

/**
 * Create a new news article.
 * Accepts a plain object — thumbnail/PDF uploads are handled separately.
 */
export const createNews = async (payload) => {
  const { data, error } = await supabase
    .from('news_updates')
    .insert(payload)
    .select()
    .single()
  if (error) throw error
  return { data }
}

/**
 * Update an existing news article.
 */
export const updateNews = async (id, updates) => {
  const { data, error } = await supabase
    .from('news_updates')
    .update(updates)
    .eq('id', id)
    .select()
    .single()
  if (error) throw error
  return { data }
}

/**
 * Delete a news article. Also removes associated storage objects.
 */
export const deleteNews = async (id) => {
  // Fetch paths before deleting row
  const { data: article, error: fetchError } = await supabase
    .from('news_updates')
    .select('thumbnail_url, pdf_url')
    .eq('id', id)
    .single()
  if (fetchError) throw fetchError

  // Remove storage objects (thumbnail + pdf) — errors are non-fatal
  const pathsToDelete = []
  if (article?.thumbnail_url) {
    const thumbPath = article.thumbnail_url.split('/news-media/').pop()
    if (thumbPath) pathsToDelete.push(thumbPath)
  }
  if (article?.pdf_url) {
    const pdfPath = article.pdf_url.split('/news-media/').pop()
    if (pdfPath) pathsToDelete.push(pdfPath)
  }
  if (pathsToDelete.length > 0) {
    await supabase.storage.from('news-media').remove(pathsToDelete).catch(() => {})
  }

  const { error } = await supabase.from('news_updates').delete().eq('id', id)
  if (error) throw error
}

/**
 * Upload a file (image or PDF) to the news-media bucket.
 * Returns the public URL.
 */
export const uploadNewsFile = async (file, onProgress) => {
  const ext      = file.name.split('.').pop().toLowerCase()
  const filename = `${crypto.randomUUID()}.${ext}`

  if (onProgress) onProgress(10)

  const { error: uploadError } = await supabase.storage
    .from('news-media')
    .upload(filename, file, { upsert: false })
  if (uploadError) throw uploadError

  if (onProgress) onProgress(90)

  const { data: { publicUrl } } = supabase.storage
    .from('news-media')
    .getPublicUrl(filename)

  if (onProgress) onProgress(100)

  return { publicUrl, filename }
}

/**
 * Delete a single file from the news-media bucket by its storage path (filename).
 * Errors are swallowed — used for cleanup when replacing images.
 */
export const deleteNewsFile = async (publicUrl) => {
  if (!publicUrl) return
  const path = publicUrl.split('/news-media/').pop()
  if (path) {
    await supabase.storage.from('news-media').remove([path]).catch(() => {})
  }
}
