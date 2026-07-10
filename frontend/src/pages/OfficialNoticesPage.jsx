import { useEffect, useState, useMemo } from 'react'
import NoticeCard from '../components/NoticeCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { getRecentNotices, NOTICE_CATEGORIES, CATEGORY_ICONS, isNoticeExpired } from '../services/notices'

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 8 }, (_, i) => CURRENT_YEAR - i)
const CLASSES = [9, 10, 11, 12]

// Status filter options
// 'active'   — visible, not yet expired
// 'archived' — visible, past their expiry date
// ''         — all (default)
const STATUS_OPTIONS = [
  { value: '',         label: 'All Notices' },
  { value: 'active',   label: 'Active' },
  { value: 'archived', label: 'Archive' },
]

export default function OfficialNoticesPage() {
  const [notices, setNotices]                   = useState([])
  const [loading, setLoading]                   = useState(true)
  const [error, setError]                       = useState(null)
  const [filterStatus, setFilterStatus]         = useState('')
  const [filterCategory, setFilterCategory]     = useState('')
  const [filterYear, setFilterYear]             = useState('')
  const [filterClass, setFilterClass]           = useState('')
  const [search, setSearch]                     = useState('')

  useEffect(() => {
    setLoading(true)
    // Pass activeOnly=false so ALL visible notices (active + archived) are loaded
    getRecentNotices(200, false)
      .then(res => setNotices(res.data))
      .catch(err => setError(err.message || 'Failed to load notices'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let list = notices

    // Status filter: active / archived / all
    if (filterStatus === 'active') {
      list = list.filter(n => !isNoticeExpired(n))
    } else if (filterStatus === 'archived') {
      list = list.filter(n => isNoticeExpired(n))
    }

    // Category, year, class filters
    if (filterCategory) list = list.filter(n => n.category === filterCategory)
    if (filterYear)     list = list.filter(n => String(n.year) === filterYear)
    if (filterClass)    list = list.filter(n => n.class_id === parseInt(filterClass))

    // Search across title, category, description
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(n =>
        n.title.toLowerCase().includes(q) ||
        n.category.toLowerCase().includes(q) ||
        (n.description || '').toLowerCase().includes(q)
      )
    }

    // Sort order:
    //   1. Pinned + Active (pinned and not expired)
    //   2. Active (not expired, not pinned)
    //   3. Pinned + Archived (pinned and expired)
    //   4. Archived (expired, not pinned)
    // Within each group: newest first (created_at DESC)
    return [...list].sort((a, b) => {
      const aExpired = isNoticeExpired(a)
      const bExpired = isNoticeExpired(b)

      // Primary: active before archived
      if (aExpired !== bExpired) return aExpired ? 1 : -1

      // Secondary: pinned first within same status group
      if (a.is_pinned !== b.is_pinned) return b.is_pinned ? 1 : -1

      // Tertiary: newest first
      return new Date(b.created_at) - new Date(a.created_at)
    })
  }, [notices, filterStatus, filterCategory, filterYear, filterClass, search])

  // Count active vs archived for the summary line
  const activeCount   = notices.filter(n => !isNoticeExpired(n)).length
  const archivedCount = notices.filter(n => isNoticeExpired(n)).length

  // Determine the visible active/archived counts within the current filtered set
  const filteredActiveCount   = filtered.filter(n => !isNoticeExpired(n)).length
  const filteredArchivedCount = filtered.filter(n => isNoticeExpired(n)).length

  const hasFilters = filterStatus || filterCategory || filterYear || filterClass || search
  const clearFilters = () => {
    setFilterStatus('')
    setFilterCategory('')
    setFilterYear('')
    setFilterClass('')
    setSearch('')
  }

  // Human-readable result summary
  const resultSummary = (() => {
    if (filterStatus === 'active')   return `${filteredActiveCount} active notice${filteredActiveCount !== 1 ? 's' : ''}`
    if (filterStatus === 'archived') return `${filteredArchivedCount} archived notice${filteredArchivedCount !== 1 ? 's' : ''}`
    return `${filtered.length} notice${filtered.length !== 1 ? 's' : ''} (${filteredActiveCount} active, ${filteredArchivedCount} archived)`
  })()

  return (
    <div>
      {/* ── Page Hero ── */}
      <section className="bg-gradient-to-br from-indigo-700 via-indigo-800 to-blue-900 text-white py-14 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <span className="inline-block bg-indigo-600 text-indigo-100 text-xs font-semibold px-3 py-1 rounded-full mb-4 tracking-wide uppercase">
            Tamil Nadu State Board
          </span>
          <h1 className="text-3xl md:text-4xl font-extrabold mb-3 leading-tight">
            Official Notices &amp; Updates
          </h1>
          <p className="text-indigo-200 text-base mb-8 max-w-xl mx-auto">
            Timetables, circulars, results, hall tickets, government orders, and all official
            education updates in one place. Archived notices remain accessible for reference.
          </p>
          {/* Inline search */}
          <div className="max-w-lg mx-auto">
            <div className="flex items-center bg-white rounded-xl px-4 py-2.5 gap-3 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
              </svg>
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search notices, timetables, circulars… (includes archive)"
                className="flex-1 text-sm text-gray-800 outline-none bg-transparent placeholder-gray-400"
              />
              {search && (
                <button onClick={() => setSearch('')} className="text-gray-400 hover:text-gray-600 text-lg leading-none">×</button>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Filters ── */}
      <section className="bg-white border-b border-gray-100 sticky top-16 z-30 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap gap-2 items-center">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide mr-1">Filter:</span>

          {/* Status filter: All / Active / Archive */}
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
            {STATUS_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setFilterStatus(opt.value)}
                className={`text-xs font-semibold px-3 py-1.5 rounded-md transition-colors ${
                  filterStatus === opt.value
                    ? 'bg-white text-indigo-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {opt.value === 'archived' && '🗂️ '}{opt.label}
              </button>
            ))}
          </div>

          {/* Category filter */}
          <select
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-200"
          >
            <option value="">All Categories</option>
            {NOTICE_CATEGORIES.map(c => (
              <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>
            ))}
          </select>

          {/* Year filter */}
          <select
            value={filterYear}
            onChange={e => setFilterYear(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-200"
          >
            <option value="">All Years</option>
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>

          {/* Class filter */}
          <select
            value={filterClass}
            onChange={e => setFilterClass(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-200"
          >
            <option value="">All Classes</option>
            {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
          </select>

          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-red-500 hover:text-red-700 font-medium px-2"
            >
              Clear
            </button>
          )}

          {/* Result count summary */}
          <span className="ml-auto text-xs text-gray-400 font-medium whitespace-nowrap">
            {loading ? '…' : resultSummary}
          </span>
        </div>
      </section>

      {/* ── Archive info banner (shown when Archive tab is active) ── */}
      {filterStatus === 'archived' && !loading && (
        <div className="max-w-7xl mx-auto px-4 pt-5">
          <div className="flex items-start gap-3 bg-gray-50 border border-gray-200 rounded-xl px-5 py-3">
            <span className="text-xl shrink-0 mt-0.5">🗂️</span>
            <p className="text-sm text-gray-600">
              <strong className="text-gray-700">Viewing archived notices.</strong>{' '}
              These notices have passed their expiry date but remain available for reference.
              All downloads, PDFs, and detail pages are still accessible.
            </p>
          </div>
        </div>
      )}

      {/* ── Content ── */}
      <section className="max-w-7xl mx-auto px-4 py-10">
        {loading && <LoadingSpinner text="Loading notices…" />}

        {error && (
          <div className="text-center py-20 text-red-500">{error}</div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
            <div className="text-5xl mb-4">{filterStatus === 'archived' ? '🗂️' : '📭'}</div>
            <p className="text-gray-700 font-semibold mb-1">
              {hasFilters
                ? filterStatus === 'archived'
                  ? 'No archived notices match your filters.'
                  : 'No notices match your filters.'
                : filterStatus === 'archived'
                  ? 'No archived notices yet.'
                  : 'No official notices published yet.'}
            </p>
            {hasFilters && (
              <button onClick={clearFilters} className="mt-3 text-sm text-indigo-600 hover:text-indigo-800 font-medium">
                Clear filters
              </button>
            )}
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {filtered.map(notice => (
              <NoticeCard key={notice.id} notice={notice} />
            ))}
          </div>
        )}

        {/* Archive count footer note — shown in All view when archived notices exist */}
        {!loading && !error && filterStatus === '' && archivedCount > 0 && (
          <p className="text-center text-xs text-gray-400 mt-8">
            {archivedCount} archived notice{archivedCount !== 1 ? 's' : ''} shown above.
            Use the <strong>Archive</strong> filter to view them exclusively.
          </p>
        )}
      </section>
    </div>
  )
}
