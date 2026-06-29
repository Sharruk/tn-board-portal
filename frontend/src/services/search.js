import { supabase } from '../lib/supabase'

// =============================================================================
// Search Service — searches Question Papers, Official Notices, and News
// =============================================================================

// ── Subject / exam-type aliases for paper search ──────────────────────────────

const SUBJECT_ALIASES = {
  maths: 'mathematics', math: 'mathematics', mathematics: 'mathematics',
  phy: 'physics', physics: 'physics',
  chem: 'chemistry', chemistry: 'chemistry',
  bio: 'biology', biology: 'biology',
  eng: 'english', english: 'english',
  tamil: 'tamil',
  cs: 'computer science', computer: 'computer science',
  history: 'history',
  geo: 'geography', geography: 'geography',
  civics: 'civics',
  economics: 'economics',
  commerce: 'commerce',
  accounts: 'accountancy', accountancy: 'accountancy',
  social: 'social science', science: 'science',
}

const EXAM_PATTERNS = [
  'monthly test',
  'unit test 1', 'unit test 2', 'unit test 3',
  'quarterly exam', 'quarterly',
  'half yearly exam', 'half yearly',
  'annual exam', 'annual',
  'public exam',
  'practical exam',
  'model exam',
]


function expandTerms(q) {
  const normalized = q.trim().toLowerCase()
  const terms = new Set([normalized])

  for (const [alias, full] of Object.entries(SUBJECT_ALIASES)) {
    if (normalized.includes(alias) && full !== normalized) {
      terms.add(full)
    }
  }

  for (const pattern of EXAM_PATTERNS) {
    if (normalized.includes(pattern) && pattern !== normalized) {
      terms.add(pattern)
    }
  }

  return [...terms]
}

// ── Individual search functions ───────────────────────────────────────────────

export const searchPapers = async ({ q, class_id, exam_type, paper_type } = {}) => {
  const rawQuery = (q || '').trim()
  if (!rawQuery) return { data: { query: '', total: 0, results: [] } }

  const terms = expandTerms(rawQuery)
  const seen = new Map()

  for (const term of terms) {
    const { data, error } = await supabase.rpc('search_papers', {
      q:            term,
      p_class_id:   class_id ? parseInt(class_id, 10) : null,
      p_exam_type:  exam_type  || null,
      p_paper_type: paper_type || null,
    })
    if (error) throw error
    data?.forEach(r => seen.set(r.id, r))
  }

  const results = [...seen.values()]

  supabase
    .from('search_queries')
    .insert({ term: rawQuery, result_count: results.length })
    .then(() => {})

  return {
    data: {
      query: rawQuery,
      total: results.length,
      results: results.map(r => ({
        _type:             'paper',
        id:                r.id,
        title:             r.title,
        exam_type:         r.exam_type,
        year:              r.year,
        paper_type:        r.paper_type,
        public_url:        r.public_url,
        original_filename: r.original_filename ?? null,
        subject_name:      r.subject_name,
        class_name:        r.class_name,
        created_at:        r.created_at,
      })),

    },
  }
}

export const searchNotices = async ({ q, category, class_id, year } = {}) => {
  const rawQuery = (q || '').trim()
  if (!rawQuery) return { data: { query: '', total: 0, results: [] } }

  const { data, error } = await supabase.rpc('search_notices', {
    q,
    p_category: category || null,
    p_class_id: class_id ? parseInt(class_id, 10) : null,
    p_year:     year     ? parseInt(year, 10)     : null,
  })
  if (error) throw error

  return {
    data: {
      query:  rawQuery,
      total:  data?.length ?? 0,
      results: (data ?? []).map(r => ({
        _type:         'notice',
        id:            r.id,
        title:         r.title,
        category:      r.category,
        class_name:    r.class_name,
        year:          r.year,
        public_url:    r.public_url,
        file_type:     r.file_type,
        is_pinned:     r.is_pinned,
        view_count:    r.view_count,
        download_count:r.download_count,
        created_at:    r.created_at,
      })),
    },
  }
}

// ── News search ───────────────────────────────────────────────────────────────

export const searchNews = async ({ q, category } = {}) => {
  const rawQuery = (q || '').trim()
  if (!rawQuery) return { data: { query: '', total: 0, results: [] } }

  const { data, error } = await supabase.rpc('search_news', {
    q:          rawQuery,
    p_category: category || null,
    p_limit:    50,
  })
  if (error) throw error

  return {
    data: {
      query:  rawQuery,
      total:  data?.length ?? 0,
      results: (data ?? []).map(r => ({
        _type:         'news',
        id:            r.id,
        title:         r.title,
        slug:          r.slug,
        summary:       r.summary,
        category:      r.category,
        thumbnail_url: r.thumbnail_url,
        youtube_url:   r.youtube_url,
        is_pinned:     r.is_pinned,
        view_count:    r.view_count,
        published_at:  r.published_at,
        created_at:    r.created_at,
      })),
    },
  }
}

// ── Combined global search (newest first across all three types) ──────────────

/**
 * Search Question Papers, Official Notices, and News simultaneously.
 * Results are merged and sorted by published_at / created_at descending.
 *
 * @param {object} opts
 * @param {string} opts.q            - Search term (required)
 * @param {string} [opts.class_id]   - Filter papers by class
 * @param {string} [opts.paper_type] - Filter papers by type ('question'|'answer_key')
 * @returns {Promise<{data: {query, total, results}}>}
 */
export const globalSearch = async ({ q, class_id, paper_type } = {}) => {
  const rawQuery = (q || '').trim()
  if (!rawQuery) return { data: { query: '', total: 0, results: [] } }

  const [papersRes, noticesRes, newsRes] = await Promise.allSettled([
    searchPapers({ q: rawQuery, class_id, paper_type }),
    searchNotices({ q: rawQuery }),
    searchNews({ q: rawQuery }),
  ])

  const paperResults  = papersRes.status  === 'fulfilled' ? papersRes.value.data.results  : []
  const noticeResults = noticesRes.status === 'fulfilled' ? noticesRes.value.data.results : []
  const newsResults   = newsRes.status    === 'fulfilled' ? newsRes.value.data.results    : []

  // Use published_at for news, created_at for papers/notices — newest first
  const getTime = (r) => {
    const d = r._type === 'news' ? (r.published_at || r.created_at) : r.created_at
    return d ? new Date(d).getTime() : 0
  }

  const merged = [...paperResults, ...noticeResults, ...newsResults].sort(
    (a, b) => getTime(b) - getTime(a)
  )

  return {
    data: {
      query:   rawQuery,
      total:   merged.length,
      results: merged,
    },
  }
}
