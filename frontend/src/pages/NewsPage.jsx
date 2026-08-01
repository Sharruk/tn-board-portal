import { useEffect, useState, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import NewsCard from '../components/NewsCard'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { getAllNews, NEWS_CATEGORIES, NEWS_CATEGORY_ICONS } from '../services/news'

const PAGE_SIZE = 12

export default function NewsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const activeCategory = searchParams.get('category') || ''

  const [articles, setArticles]   = useState([])
  const [total, setTotal]         = useState(0)
  const [offset, setOffset]       = useState(0)
  const [loading, setLoading]     = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError]         = useState(null)

  const load = useCallback(async (cat, off, append = false) => {
    if (!append) setLoading(true)
    else setLoadingMore(true)
    setError(null)
    try {
      const res = await getAllNews({ category: cat || null, limit: PAGE_SIZE, offset: off })
      setArticles(prev => append ? [...prev, ...res.data] : res.data)
      setTotal(res.count)
    } catch (err) {
      setError(err.message || 'Failed to load news')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [])

  // Reload when category filter changes
  useEffect(() => {
    setOffset(0)
    load(activeCategory, 0, false)
  }, [activeCategory, load])

  const handleCategoryChange = (cat) => {
    const next = new URLSearchParams()
    if (cat) next.set('category', cat)
    setSearchParams(next)
  }

  const handleLoadMore = () => {
    const newOffset = offset + PAGE_SIZE
    setOffset(newOffset)
    load(activeCategory, newOffset, true)
  }

  const hasMore = articles.length < total

  return (
    <div className="max-w-7xl mx-auto px-4 py-10">
      {/* Page header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-3xl">📰</span>
          <h1 className="text-3xl font-extrabold text-gray-900">News &amp; Updates</h1>
        </div>
        <p className="text-gray-500 text-sm mt-1">
          Education news, holiday announcements, exam updates, government circulars, and more.
        </p>
      </div>

      {/* Category filter pills */}
      <div className="flex flex-wrap gap-2 mb-8">
        <button
          onClick={() => handleCategoryChange('')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
            !activeCategory
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300 hover:text-blue-600'
          }`}
        >
          All News
        </button>
        {NEWS_CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => handleCategoryChange(cat)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium border transition-colors ${
              activeCategory === cat
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300 hover:text-blue-600'
            }`}
          >
            {NEWS_CATEGORY_ICONS[cat]} {cat}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner text="Loading news…" />
      ) : error ? (
        <ErrorMessage message={error} />
      ) : articles.length === 0 ? (
        <div className="text-center py-24 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
          <div className="text-5xl mb-4">📭</div>
          <p className="text-gray-500 font-medium">
            {activeCategory ? `No articles in "${activeCategory}" yet.` : 'No news articles published yet.'}
          </p>
          {activeCategory && (
            <button
              onClick={() => handleCategoryChange('')}
              className="mt-4 text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              View all categories →
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Result count */}
          <p className="text-sm text-gray-400 mb-5">
            {total} article{total !== 1 ? 's' : ''}
            {activeCategory ? ` in "${activeCategory}"` : ''}
          </p>

          {/* Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {articles.map(article => (
              <NewsCard key={article.id} article={article} />
            ))}
          </div>

          {/* Load More */}
          {hasMore && (
            <div className="mt-10 text-center">
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="btn-secondary px-8"
              >
                {loadingMore ? (
                  <><span className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" /> Loading…</>
                ) : (
                  `Load More (${total - articles.length} remaining)`
                )}
              </button>
            </div>
          )}
        </>
      )}

      {/* Back link */}
      <div className="mt-10">
        <Link to="/" className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
          ← Back to Home
        </Link>
      </div>
    </div>
  )
}
