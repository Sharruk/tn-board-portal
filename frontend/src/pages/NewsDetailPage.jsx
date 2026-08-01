import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import NewsCard from '../components/NewsCard'
import {
  getNewsBySlug,
  getRelatedNews,
  recordNewsView,
  NEWS_CATEGORY_ICONS,
  formatPublishedDate,
} from '../services/news'
import { getYouTubeEmbedUrl } from '../services/notices'

// =============================================================================
// Sub-components
// =============================================================================

function Toast({ message, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2800)
    return () => clearTimeout(t)
  }, [onDone])
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-fade-in">
      <div className="flex items-center gap-2 bg-gray-900 text-white text-sm font-medium px-5 py-3 rounded-full shadow-xl">
        <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
        </svg>
        {message}
      </div>
    </div>
  )
}

/** Share menu — identical pattern to NoticeDetailPage */
function ShareMenu({ title, url, onDone }) {
  const [open, setOpen] = useState(false)
  const shareOptions = [
    {
      label: 'Copy Link', icon: '🔗',
      action: async () => {
        try { await navigator.clipboard.writeText(url); onDone('Link copied!') }
        catch { onDone('Copy this link: ' + url) }
        setOpen(false)
      },
    },
    {
      label: 'WhatsApp', icon: '💬',
      action: () => { window.open(`https://wa.me/?text=${encodeURIComponent(title + '\n' + url)}`, '_blank'); setOpen(false) },
    },
    {
      label: 'Telegram', icon: '✈️',
      action: () => { window.open(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`, '_blank'); setOpen(false) },
    },
    {
      label: 'Email', icon: '📧',
      action: () => { window.open(`mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`, '_blank'); setOpen(false) },
    },
  ]
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-600 font-semibold px-4 py-2.5 rounded-xl border border-gray-200 transition-colors text-sm"
        title="Share"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
        </svg>
        <span className="hidden sm:inline">Share</span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 z-50 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 w-44">
            {shareOptions.map(opt => (
              <button
                key={opt.label}
                onClick={opt.action}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
              >
                <span className="text-lg">{opt.icon}</span>
                {opt.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

/** Render article content — paragraphs split on double newlines */
function ArticleContent({ content }) {
  if (!content) return null
  const paragraphs = content.split(/\n\n+/).filter(Boolean)
  return (
    <div className="prose-sm text-gray-700 leading-relaxed space-y-4">
      {paragraphs.map((para, i) => (
        <p key={i} className="whitespace-pre-wrap">{para}</p>
      ))}
    </div>
  )
}

// =============================================================================
// NewsDetailPage
// =============================================================================

export default function NewsDetailPage() {
  const { slug } = useParams()
  const [article, setArticle]   = useState(null)
  const [related, setRelated]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [toast, setToast]       = useState(null)
  const [viewCount, setViewCount] = useState(0)

  const showToast = useCallback(msg => setToast(msg), [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    getNewsBySlug(slug)
      .then(res => {
        const a = res.data
        setArticle(a)
        setViewCount(a.view_count ?? 0)
        recordNewsView(a.id)
        setViewCount(c => c + 1)
        if (a.category) {
          getRelatedNews(a.category, a.id, 4)
            .then(r => setRelated(r.data))
            .catch(() => {})
        }
      })
      .catch(err => setError(err.message || 'Article not found'))
      .finally(() => setLoading(false))
  }, [slug])

  if (loading) return <div className="max-w-4xl mx-auto px-4 py-12"><LoadingSpinner text="Loading article…" /></div>
  if (error)   return <div className="max-w-4xl mx-auto px-4 py-12"><ErrorMessage message={error} /></div>
  if (!article) return null

  const icon        = NEWS_CATEGORY_ICONS[article.category] ?? '📰'
  const publishedOn = formatPublishedDate(article.published_at || article.created_at)
  const embedUrl    = article.youtube_url ? getYouTubeEmbedUrl(article.youtube_url) : null

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}

      {/* SEO meta — basic title update */}
      <title>{article.title} | TN Board News</title>

      {/* Breadcrumb */}
      <Breadcrumb items={[
        { label: 'Home', href: '/' },
        { label: 'News & Updates', href: '/news' },
        { label: article.category, href: `/news?category=${encodeURIComponent(article.category)}` },
        { label: article.title },
      ]} />

      <div className="mt-6 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {/* Hero thumbnail */}
        {article.thumbnail_url && (
          <div className="w-full overflow-hidden" style={{ maxHeight: '420px' }}>
            <img
              src={article.thumbnail_url}
              alt={article.thumbnail_alt || article.title}
              className="w-full object-cover"
              style={{ maxHeight: '420px' }}
            />
          </div>
        )}

        <div className="p-6 sm:p-8">
          {/* Pinned banner */}
          {article.is_pinned && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5 mb-5">
              <span className="text-amber-500 text-lg">📌</span>
              <p className="text-sm font-semibold text-amber-700">This is a pinned article.</p>
            </div>
          )}

          {/* Category + title */}
          <div className="mb-5">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 mb-3">
              {icon} {article.category}
            </span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 leading-snug">
              {article.title}
            </h1>
          </div>

          {/* Meta grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Category',  value: article.category },
              { label: 'Published', value: publishedOn },
              { label: 'Class',     value: article.class_name || 'All' },
              { label: 'Views',     value: viewCount > 0 ? `${viewCount.toLocaleString()} view${viewCount !== 1 ? 's' : ''}` : '—' },
            ].map(m => (
              <div key={m.label} className="bg-gray-50 rounded-xl p-3">
                <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{m.label}</p>
                <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate">{m.value}</p>
              </div>
            ))}
          </div>

          {/* Tags */}
          {article.tags && article.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-5">
              {article.tags.map(tag => (
                <span key={tag} className="badge bg-gray-100 text-gray-600 text-xs">#{tag}</span>
              ))}
            </div>
          )}

          {/* Summary */}
          {article.summary && (
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6">
              <p className="text-sm font-medium text-blue-900 leading-relaxed">{article.summary}</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex flex-wrap gap-3 mb-6">
            {article.pdf_url && (
              <a
                href={article.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-5 py-2.5 rounded-xl transition-colors text-sm"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
                </svg>
                Download PDF
              </a>
            )}
            <ShareMenu title={article.title} url={window.location.href} onDone={showToast} />
          </div>

          {/* YouTube Embed */}
          {embedUrl && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-bold text-gray-700 flex items-center gap-2">
                  <span className="text-red-600">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                      <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
                    </svg>
                  </span>
                  Watch Video
                </h2>
                <a
                  href={article.youtube_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
                >
                  Watch on YouTube
                </a>
              </div>
              <div
                className="rounded-2xl overflow-hidden border border-gray-200 bg-black"
                style={{ position: 'relative', paddingTop: '56.25%' }}
              >
                <iframe
                  src={embedUrl}
                  title={`${article.title} — YouTube Video`}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
                />
              </div>
            </div>
          )}

          {/* Full article content */}
          {article.content && (
            <div className="border-t border-gray-100 pt-6">
              <h2 className="text-base font-bold text-gray-700 mb-4">Full Article</h2>
              <ArticleContent content={article.content} />
            </div>
          )}

          {/* District info */}
          {article.district && (
            <div className="mt-6 flex items-center gap-2 text-sm text-gray-500">
              <span>📍</span>
              <span>Applicable to: <strong className="text-gray-700">{article.district}</strong></span>
            </div>
          )}
        </div>
      </div>

      {/* Related Articles */}
      {related.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              More {article.category} News
            </h2>
            <Link
              to={`/news?category=${encodeURIComponent(article.category)}`}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              View all →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {related.map(a => <NewsCard key={a.id} article={a} />)}
          </div>
        </div>
      )}

      {/* Back link */}
      <div className="mt-8">
        <Link to="/news" className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
          ← Back to News &amp; Updates
        </Link>
      </div>
    </div>
  )
}
