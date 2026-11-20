import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import StudyMaterialCard from '../components/StudyMaterialCard'
import { getStudyMaterials, MATERIAL_MEDIUMS } from '../services/studyMaterials'
import { getMaterialCategories } from '../services/materialCategories'
import { getClasses } from '../services/classes'
import { getSubjectsForClass } from '../services/classes'

export default function StudyMaterialsPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  const [materials, setMaterials] = useState([])
  const [categories, setCategories] = useState([])
  const [classes, setClasses] = useState([])
  const [subjects, setSubjects] = useState([])
  const [totalCount, setTotalCount] = useState(0)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // URL-driven filter states
  const classId = searchParams.get('class_id') || ''
  const subjectId = searchParams.get('subject_id') || ''
  const categoryId = searchParams.get('category_id') || ''
  const medium = searchParams.get('medium') || 'all'
  const search = searchParams.get('search') || ''
  const [searchInput, setSearchInput] = useState(search)

  // 1. Load initial categories & classes
  useEffect(() => {
    Promise.allSettled([
      getMaterialCategories(),
      getClasses(),
    ]).then(([catRes, clsRes]) => {
      if (catRes.status === 'fulfilled') {
        const catData = catRes.value?.data || catRes.value || []
        setCategories(Array.isArray(catData) ? catData : [])
      }
      if (clsRes.status === 'fulfilled') {
        setClasses(clsRes.value?.data || [])
      }
    })
  }, [])

  // 2. Load subjects when classId changes
  useEffect(() => {
    if (classId) {
      getSubjectsForClass(classId)
        .then(res => setSubjects(res.data || []))
        .catch(() => setSubjects([]))
    } else {
      setSubjects([])
    }
  }, [classId])

  // 3. Fetch materials on filter changes
  useEffect(() => {
    setLoading(true)
    setError(null)

    getStudyMaterials({
      class_id: classId || undefined,
      subject_id: subjectId || undefined,
      category_id: categoryId || undefined,
      medium: medium !== 'all' ? medium : undefined,
      search: search || undefined,
      limit: 50,
    })
      .then(res => {
        setMaterials(res.data || [])
        setTotalCount(res.total || 0)
      })
      .catch(err => {
        setError(err.message || 'Failed to load study materials')
        setMaterials([])
      })
      .finally(() => setLoading(false))
  }, [classId, subjectId, categoryId, medium, search])

  const updateParam = (key, value) => {
    const next = new URLSearchParams(searchParams)
    if (value && value !== 'all') {
      next.set(key, value)
    } else {
      next.delete(key)
    }
    // Reset subject if class changes
    if (key === 'class_id') {
      next.delete('subject_id')
    }
    setSearchParams(next)
  }

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    updateParam('search', searchInput.trim())
  }

  const clearAllFilters = () => {
    setSearchInput('')
    setSearchParams({})
  }

  const hasActiveFilters = Boolean(classId || subjectId || categoryId || (medium && medium !== 'all') || search)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Breadcrumb items={[{ label: 'Home', href: '/' }, { label: 'Study Materials' }]} />

      {/* Header */}
      <div className="mt-4 mb-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100 mb-2">
              <span>📚</span>
              <span>Tamil Nadu State Board Notes &amp; Resources</span>
            </div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">Study Materials Hub</h1>
            <p className="text-gray-500 text-sm mt-1">
              Curated chapter notes, question banks, formula sheets, blueprints, and study guides for Classes 9 to 12.
            </p>
          </div>

          <Link
            to="/submit-material"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-xs transition-colors shrink-0 self-start md:self-auto"
          >
            <span>📤</span> Submit Study Material
          </Link>
        </div>
      </div>

      {/* Filter Section */}
      <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-xs mb-8 space-y-4">
        {/* Row 1: Search and Class pills */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center gap-4 justify-between">
          {/* Search form */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
            <input
              type="text"
              placeholder="Search by title, chapter, tag, author…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-10 pr-20 py-2 text-sm bg-gray-50 hover:bg-gray-100/80 focus:bg-white border border-gray-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
            />
            <svg
              className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <button
              type="submit"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition"
            >
              Search
            </button>
          </form>

          {/* Class selection buttons */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 lg:pb-0">
            <span className="text-xs font-medium text-gray-500 mr-1 shrink-0">Class:</span>
            <button
              type="button"
              onClick={() => updateParam('class_id', '')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                !classId
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All
            </button>
            {[9, 10, 11, 12].map(c => (
              <button
                key={c}
                type="button"
                onClick={() => updateParam('class_id', String(c))}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition ${
                  String(classId) === String(c)
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Class {c}
              </button>
            ))}
          </div>
        </div>

        {/* Row 2: Secondary Filters (Subject, Medium, Categories) */}
        <div className="pt-3 border-t border-gray-100 flex flex-wrap items-center gap-3">
          {/* Subject Dropdown (if class is chosen) */}
          {classId && subjects.length > 0 && (
            <select
              value={subjectId}
              onChange={(e) => updateParam('subject_id', e.target.value)}
              className="text-xs font-medium bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-gray-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="">All Subjects</option>
              {subjects.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          )}

          {/* Medium Dropdown */}
          <select
            value={medium}
            onChange={(e) => updateParam('medium', e.target.value)}
            className="text-xs font-medium bg-gray-50 border border-gray-200 rounded-xl px-3 py-2 text-gray-700 focus:outline-hidden focus:ring-2 focus:ring-blue-500/20"
          >
            <option value="all">All Mediums</option>
            <option value="both">Both (Tamil &amp; English)</option>
            <option value="tamil">Tamil Medium (தமிழ்)</option>
            <option value="english">English Medium</option>
          </select>

          {/* Category Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto flex-1 py-1">
            <button
              type="button"
              onClick={() => updateParam('category_id', '')}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium shrink-0 transition ${
                !categoryId
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All Categories
            </button>
            {categories.map(cat => (
              <button
                key={cat.id}
                type="button"
                onClick={() => updateParam('category_id', String(cat.id))}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium shrink-0 transition flex items-center gap-1.5 ${
                  String(categoryId) === String(cat.id)
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat.icon && <span>{cat.icon}</span>}
                <span>{cat.name}</span>
              </button>
            ))}
          </div>

          {/* Clear filters button */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={clearAllFilters}
              className="text-xs text-rose-600 hover:text-rose-700 font-semibold underline px-2 py-1 ml-auto"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="py-16">
          <LoadingSpinner text="Loading study materials…" />
        </div>
      ) : error ? (
        <ErrorMessage message={error} />
      ) : materials.length === 0 ? (
        <div className="text-center py-16 bg-gray-50 rounded-2xl border border-dashed border-gray-200 p-8">
          <div className="text-4xl mb-3">📖</div>
          <h3 className="text-lg font-bold text-gray-800">No study materials found</h3>
          <p className="text-gray-500 text-sm mt-1 max-w-md mx-auto">
            {hasActiveFilters
              ? 'Try relaxing your filters or search keywords to see more study materials.'
              : 'Study materials are being compiled for Tamil Nadu State Board classes. Check back soon or contribute!'}
          </p>
          {hasActiveFilters ? (
            <button
              onClick={clearAllFilters}
              className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-700 transition"
            >
              Clear All Filters
            </button>
          ) : (
            <Link
              to="/submit-material"
              className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-700 transition"
            >
              Contribute First Material
            </Link>
          )}
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-semibold text-gray-500">
              Showing {materials.length} {materials.length === 1 ? 'material' : 'materials'}
              {totalCount > materials.length && ` of ${totalCount}`}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {materials.map(item => (
              <StudyMaterialCard key={item.id} item={item} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
