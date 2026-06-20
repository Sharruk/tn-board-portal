import { supabase } from '../lib/supabase'

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

function expandTerms(q) {
  const normalized = q.trim().toLowerCase()
  const terms = new Set([normalized])
  for (const [alias, full] of Object.entries(SUBJECT_ALIASES)) {
    if (normalized.includes(alias) && full !== normalized) {
      terms.add(full)
    }
  }
  return [...terms]
}

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
    if (!error && data) {
      data.forEach(r => seen.set(r.id, r))
    }
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
        id:           r.id,
        title:        r.title,
        exam_type:    r.exam_type,
        year:         r.year,
        paper_type:   r.paper_type,
        public_url:   r.public_url,
        subject_name: r.subject_name,
        class_name:   r.class_name,
      })),
    },
  }
}
