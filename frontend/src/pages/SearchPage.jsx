import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import SearchBar from '../components/SearchBar'
import LoadingSpinner from '../components/LoadingSpinner'
import { globalSearch } from '../services/search'
import { downloadPaper } from '../utils/download'
import { CATEGORY_ICONS } from '../services/notices'
import { NEWS_CATEGORY_ICONS, formatPublishedDate } from '../services/news'

// ── Suggestion chips ──────────────────────────────────────────────────────────

const SUGGESTIONS = [
  'Mathematics', 'Physics', 'Chemistry', 'Biology', 'Science',
  'Monthly Test', 'Annual Exam', 'Quarterly Exam', 'Half Yearly Exam', 'Answer Key',
  'Monthly Test Timetable', 'Public Exam Timetable', 'Hall Ticket', 'Results', 'TNEA Counselling',
  'Government Circular', 'Scholarships',
]


function SuggestionChip({ label, onClick }) {
  return (
    <button
      onClick={() => onClick(label)}
      className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
    >
      {label}
    </button>
  )
}

// ── Result card ───────────────────────────────────────────────────────────────

function PaperResult({ r }) {
  return (
    <Link
      to={`/paper/${r.id}`}
      className="card p-4 flex items-start sm:items-center gap-4 hover:border-blue-200 flex-col sm:flex-row"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className={`badge text-xs ${r.paper_type === 'question' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
            {r.paper_type === 'question' ? '📄 Q Paper' : '✅ Answer Key'}
          </span>
          <span className="badge bg-gray-100 text-gray-600 text-xs">{r.class_name}</span>
          <span className="badge bg-purple-100 text-purple-600 text-xs">{r.subject_name}</span>
          <span className="badge bg-gray-100 text-gray-600 text-xs">{r.exam_type}</span>
          <span className="badge bg-gray-100 text-gray-600 text-xs">{r.year}</span>
        </div>
        <h3 className="font-semibold text-gray-800 leading-snug">{r.title}</h3>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        {r.public_url && (
          <button
            onClick={e => { e.preventDefault(); e.stopPropagation(); downloadPaper(r.public_url, r.title, r.original_filename) }}
            className="btn-secondary text-sm px-3 py-1.5"
          >
            Download
          </button>
        )}

        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  )
}

function NoticeResult({ r }) {
  const icon = CATEGORY_ICONS[r.category] ?? '📄'
  const published = r.created_at
    ? new Date(r.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    : ''
  return (
    <Link
      to={`/notice/${r.id}`}
      className="card p-4 flex items-start sm:items-center gap-4 hover:border-indigo-200 flex-col sm:flex-row"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="badge text-xs bg-indigo-100 text-indigo-700">
            {icon} Official Notice
          </span>
          <span className="badge bg-gray-100 text-gray-600 text-xs">{r.category}</span>
          {r.class_name && <span className="badge bg-gray-100 text-gray-600 text-xs">{r.class_name}</span>}
          <span className="badge bg-gray-100 text-gray-600 text-xs">{r.year}</span>
          {r.is_pinned && <span className="badge bg-amber-100 text-amber-700 text-xs">📌 Pinned</span>}
        </div>
        <h3 className="font-semibold text-gray-800 leading-snug">{r.title}</h3>
        {published && <p className="text-xs text-gray-400 mt-0.5">Published {published}</p>}
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="badge bg-indigo-50 text-indigo-600 text-xs">View →</span>
        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  )
}

function NewsResult({ r }) {
  const icon      = NEWS_CATEGORY_ICONS[r.category] ?? '📰'
  const published = r.published_at
    ? formatPublishedDate(r.published_at, { short: true })
    : r.created_at
      ? new Date(r.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
      : ''
  return (
    <Link
      to={`/news/${r.slug}`}
      className="card p-4 flex items-start sm:items-center gap-4 hover:border-blue-200 flex-col sm:flex-row"
    >
      {/* Thumbnail */}
      {r.thumbnail_url && (
        <img
          src={r.thumbnail_url}
          alt={r.title}
          className="w-16 h-12 rounded-xl object-cover shrink-0 hidden sm:block"
        />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1 flex-wrap">
          <span className="badge text-xs bg-blue-100 text-blue-800">
            📰 News
          </span>
          <span className="badge bg-gray-100 text-gray-600 text-xs">{icon} {r.category}</span>
          {r.is_pinned && <span className="badge bg-amber-100 text-amber-700 text-xs">📌 Pinned</span>}
          {r.youtube_url && (
            <span className="badge bg-red-100 text-red-700 text-xs">▶ Video</span>
          )}
        </div>
        <h3 className="font-semibold text-gray-800 leading-snug">{r.title}</h3>
        {r.summary && <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{r.summary}</p>}
        {published && <p className="text-xs text-gray-400 mt-0.5">📅 {published}</p>}
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="badge bg-blue-50 text-blue-600 text-xs">Read →</span>
        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-300 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  )
}

// =============================================================================
// SearchPage
// =============================================================================

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const query       = searchParams.get('q') || ''
  const filterClass = searchParams.get('class_id') || ''
  const filterType  = searchParams.get('paper_type') || ''

  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  useEffect(() => {
    if (!query.trim()) { setResults(null); return }
    setLoading(true)
    setError(null)
    const params = { q: query }
    if (filterClass) params.class_id   = filterClass
    if (filterType)  params.paper_type = filterType
    globalSearch(params)
      .then(res => setResults(res.data))
      .catch(err => setError(err.message || 'Search failed'))
      .finally(() => setLoading(false))
  }, [query, filterClass, filterType])

  const updateFilter = (key, value) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    setSearchParams(next)
  }

  const handleSuggestion = (term) => {
    const next = new URLSearchParams(searchParams)
    next.set('q', term)
    next.delete('class_id')
    next.delete('paper_type')
    setSearchParams(next)
  }

  const paperCount  = results?.results.filter(r => r._type === 'paper').length  ?? 0
  const noticeCount = results?.results.filter(r => r._type === 'notice').length ?? 0
  const newsCount   = results?.results.filter(r => r._type === 'news').length   ?? 0

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-extrabold text-gray-900 mb-2">Search</h1>
      <p className="text-gray-500 text-sm mb-6">Search question papers, answer keys, official notices, and news articles together.</p>
      <SearchBar initialValue={query} size="md" />

      {/* Filters */}
      <div className="mt-6 flex flex-wrap gap-3 items-center">
        <span className="text-sm text-gray-500 font-medium">Filters:</span>

        <select
          value={filterClass}
          onChange={e => updateFilter('class_id', e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-blue-100"
        >
          <option value="">All Classes</option>
          {[9, 10, 11, 12].map(c => <option key={c} value={c}>Class {c}</option>)}
        </select>

        <select
          value={filterType}
          onChange={e => updateFilter('paper_type', e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-blue-100"
        >
          <option value="">All Types</option>
          <option value="question">Question Paper</option>
          <option value="answer_key">Answer Key</option>
        </select>

        {(filterClass || filterType) && (
          <button
            onClick={() => { updateFilter('class_id', ''); updateFilter('paper_type', '') }}
            className="text-sm text-red-500 hover:text-red-700 font-medium"
          >
            Clear filters
          </button>
        )}
      </div>

      <div className="mt-8">
        {loading && <LoadingSpinner text="Searching…" />}

        {error && (
          <div className="text-center py-16 text-red-500">{error}</div>
        )}

        {!loading && !query && (
          <div className="text-center py-16 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
            <div className="text-5xl mb-4">🔍</div>
            <p className="text-gray-500 font-medium">Search question papers, timetables, circulars &amp; more</p>
            <p className="text-gray-400 text-sm mt-1 mb-6">Try: "Class 10 Maths Annual Exam", "Public Exam Timetable", "TNEA"</p>
            <div className="flex flex-wrap justify-center gap-2 px-6">
              {SUGGESTIONS.map(s => (
                <SuggestionChip key={s} label={s} onClick={handleSuggestion} />
              ))}
            </div>
          </div>
        )}

        {!loading && results && (
          <>
            {/* Result summary */}
            <div className="flex items-center gap-3 mb-4 flex-wrap">
              <p className="text-sm text-gray-500">
                {results.total === 0
                  ? `No results for "${results.query}"`
                  : `${results.total} result${results.total !== 1 ? 's' : ''} for "${results.query}"`}
              </p>
              {results.total > 0 && (
                <div className="flex items-center gap-2">
                  {paperCount > 0 && (
                    <span className="badge text-xs bg-blue-100 text-blue-700">📄 {paperCount} Paper{paperCount !== 1 ? 's' : ''}</span>
                  )}
                  {noticeCount > 0 && (
                    <span className="badge text-xs bg-indigo-100 text-indigo-700">📢 {noticeCount} Notice{noticeCount !== 1 ? 's' : ''}</span>
                  )}
                  {newsCount > 0 && (
                    <span className="badge text-xs bg-blue-100 text-blue-800">📰 {newsCount} News</span>
                  )}
                </div>
              )}
            </div>

            {results.total === 0 ? (
              <div className="text-center py-16 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
                <div className="text-5xl mb-4">📭</div>
                <p className="text-gray-700 font-semibold mb-1">No results for "{results.query}"</p>
                <p className="text-gray-400 text-sm mb-6">Try one of these suggestions instead:</p>
                <div className="flex flex-wrap justify-center gap-2 px-6">
                  {SUGGESTIONS.map(s => (
                    <SuggestionChip key={s} label={s} onClick={handleSuggestion} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {results.results.map(r =>
                  r._type === 'paper'
                    ? <PaperResult  key={`paper-${r.id}`}  r={r} />
                    : r._type === 'notice'
                      ? <NoticeResult key={`notice-${r.id}`} r={r} />
                      : <NewsResult   key={`news-${r.id}`}   r={r} />
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
