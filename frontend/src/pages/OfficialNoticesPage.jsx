import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import NoticeCard from '../components/NoticeCard'
import LoadingSpinner from '../components/LoadingSpinner'
import SearchBar from '../components/SearchBar'
import { getRecentNotices, NOTICE_CATEGORIES, CATEGORY_ICONS } from '../services/notices'

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 8 }, (_, i) => CURRENT_YEAR - i)
const CLASSES = [9, 10, 11, 12]

export default function OfficialNoticesPage() {
  const [notices, setNotices]         = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [filterCategory, setFilterCategory] = useState('')
  const [filterYear, setFilterYear]   = useState('')
  const [filterClass, setFilterClass] = useState('')
  const [search, setSearch]           = useState('')

  useEffect(() => {
    setLoading(true)
    getRecentNotices(100)
      .then(res => setNotices(res.data))
      .catch(err => setError(err.message || 'Failed to load notices'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let list = notices
    if (filterCategory) list = list.filter(n => n.category === filterCategory)
    if (filterYear)     list = list.filter(n => String(n.year) === filterYear)
    if (filterClass)    list = list.filter(n => n.class_id === parseInt(filterClass))
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(n =>
        n.title.toLowerCase().includes(q) ||
        n.category.toLowerCase().includes(q) ||
        (n.description || '').toLowerCase().includes(q)
      )
    }
    // Pinned first, then newest
    return [...list].sort((a, b) => {
      if (b.is_pinned !== a.is_pinned) return b.is_pinned ? 1 : -1
      return new Date(b.created_at) - new Date(a.created_at)
    })
  }, [notices, filterCategory, filterYear, filterClass, search])

  const hasFilters = filterCategory || filterYear || filterClass || search
  const clearFilters = () => { setFilterCategory(''); setFilterYear(''); setFilterClass(''); setSearch('') }

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
            education updates in one place.
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
                placeholder="Search notices, timetables, circulars…"
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

          <select
            value={filterYear}
            onChange={e => setFilterYear(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-200"
          >
            <option value="">All Years</option>
            {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
          </select>

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

          <span className="ml-auto text-xs text-gray-400 font-medium">
            {filtered.length} notice{filtered.length !== 1 ? 's' : ''}
          </span>
        </div>
      </section>

      {/* ── Content ── */}
      <section className="max-w-7xl mx-auto px-4 py-10">
        {loading && <LoadingSpinner text="Loading notices…" />}

        {error && (
          <div className="text-center py-20 text-red-500">{error}</div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-20 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-700 font-semibold mb-1">
              {hasFilters ? 'No notices match your filters.' : 'No official notices published yet.'}
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
      </section>
    </div>
  )
}
