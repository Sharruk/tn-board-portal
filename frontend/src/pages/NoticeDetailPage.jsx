import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import NoticeCard from '../components/NoticeCard'
import {
  getNotice,
  getRelatedNotices,
  recordNoticeView,
  recordNoticeDownload,
  CATEGORY_ICONS,
  getOfficeViewerUrl,
  getYouTubeEmbedUrl,
} from '../services/notices'

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

/** Render a preview of the file based on its type. */
function FilePreview({ notice }) {
  const { public_url, file_type, title } = notice

  if (!public_url) return null

  if (file_type === 'pdf') {
    return (
      <div className="mt-6">
        <h2 className="text-base font-bold text-gray-700 mb-3 flex items-center gap-2">
          <span className="text-red-500">📄</span> PDF Preview
        </h2>
        <div className="rounded-2xl overflow-hidden border border-gray-200 bg-gray-50" style={{ height: '70vh' }}>
          <iframe
            src={public_url}
            title={title}
            className="w-full h-full"
          />
        </div>
      </div>
    )
  }

  if (file_type === 'image') {
    return (
      <div className="mt-6">
        <h2 className="text-base font-bold text-gray-700 mb-3 flex items-center gap-2">
          <span>🖼️</span> Image Preview
        </h2>
        <div className="rounded-2xl overflow-hidden border border-gray-200">
          <img
            src={public_url}
            alt={title}
            className="w-full object-contain max-h-[70vh]"
          />
        </div>
      </div>
    )
  }

  if (['docx', 'xlsx', 'pptx'].includes(file_type)) {
    const viewerUrl = getOfficeViewerUrl(public_url)
    const typeLabel = file_type === 'docx' ? 'Word Document' : file_type === 'xlsx' ? 'Excel Spreadsheet' : 'PowerPoint Presentation'
    return (
      <div className="mt-6">
        <h2 className="text-base font-bold text-gray-700 mb-3 flex items-center gap-2">
          <span>📊</span> {typeLabel} Preview
        </h2>
        <div className="rounded-2xl overflow-hidden border border-gray-200 bg-gray-50" style={{ height: '70vh' }}>
          <iframe
            src={viewerUrl}
            title={title}
            className="w-full h-full"
          />
        </div>
      </div>
    )
  }

  // Other file types — no preview available
  return (
    <div className="mt-6 bg-gray-50 border border-gray-200 rounded-2xl px-6 py-8 flex flex-col items-center text-center">
      <span className="text-5xl mb-3">📁</span>
      <p className="text-sm font-semibold text-gray-700">Preview not available for this file type.</p>
      <p className="text-xs text-gray-400 mt-1">Download the file to view it.</p>
    </div>
  )
}

/** Share options: Copy link, WhatsApp, Telegram, Email */
function ShareMenu({ title, url, onDone }) {
  const [open, setOpen] = useState(false)

  const shareOptions = [
    {
      label: 'Copy Link',
      icon: '🔗',
      action: async () => {
        try { await navigator.clipboard.writeText(url); onDone('Link copied!') }
        catch { onDone('Copy this link: ' + url) }
        setOpen(false)
      },
    },
    {
      label: 'WhatsApp',
      icon: '💬',
      action: () => {
        window.open(`https://wa.me/?text=${encodeURIComponent(title + '\n' + url)}`, '_blank')
        setOpen(false)
      },
    },
    {
      label: 'Telegram',
      icon: '✈️',
      action: () => {
        window.open(`https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`, '_blank')
        setOpen(false)
      },
    },
    {
      label: 'Email',
      icon: '📧',
      action: () => {
        window.open(`mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(url)}`, '_blank')
        setOpen(false)
      },
    },
  ]

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-600 font-semibold px-4 py-3 rounded-xl border border-gray-200 transition-colors text-base"
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

// =============================================================================
// NoticeDetailPage
// =============================================================================

export default function NoticeDetailPage() {
  const { id } = useParams()
  const [notice, setNotice]           = useState(null)
  const [related, setRelated]         = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [toast, setToast]             = useState(null)
  const [downloadCount, setDownloadCount] = useState(0)
  const [viewCount, setViewCount]     = useState(0)

  const showToast = useCallback(msg => setToast(msg), [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    getNotice(id)
      .then(res => {
        const n = res.data
        setNotice(n)
        setDownloadCount(n.download_count ?? 0)
        setViewCount(n.view_count ?? 0)
        // Increment view count (fire-and-forget)
        recordNoticeView(n.id)
        setViewCount(c => c + 1)
        // Load related notices
        if (n.category) {
          getRelatedNotices(n.category, n.id)
            .then(r => setRelated(r.data))
            .catch(() => {})
        }
      })
      .catch(err => setError(err.message || 'Notice not found'))
      .finally(() => setLoading(false))
  }, [id])

  const handleDownload = useCallback(() => {
    if (!notice?.public_url) return
    recordNoticeDownload(notice.id)
      .then(() => setDownloadCount(c => c + 1))
      .catch(() => {})
    const a = document.createElement('a')
    a.href = notice.public_url
    a.download = notice.title || 'notice'
    a.target = '_blank'
    a.click()
  }, [notice])

  if (loading) return <div className="max-w-4xl mx-auto px-4 py-12"><LoadingSpinner text="Loading notice…" /></div>
  if (error) return <div className="max-w-4xl mx-auto px-4 py-12"><ErrorMessage message={error} /></div>
  if (!notice) return null

  const icon        = CATEGORY_ICONS[notice.category] ?? '📄'
  const publishedOn = notice.created_at
    ? new Date(notice.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })
    : '—'
  const isExpired   = notice.expires_at && new Date(notice.expires_at) < new Date()
  const expiresOn   = notice.expires_at
    ? new Date(notice.expires_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })
    : null

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}

      {/* Breadcrumb */}
      <Breadcrumb items={[
        { label: 'Home', href: '/' },
        { label: 'Official Notices', href: '/official-notices' },
        { label: notice.category, href: `/official-notices?category=${encodeURIComponent(notice.category)}` },
        { label: notice.title },
      ]} />

      <div className="mt-6 bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sm:p-8">
        {/* Pinned / Expired banners */}
        {notice.is_pinned && (
          <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-xl px-4 py-2.5 mb-5">
            <span className="text-amber-500 text-lg">📌</span>
            <p className="text-sm font-semibold text-amber-700">This is a pinned official notice.</p>
          </div>
        )}
        {isExpired && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 mb-5">
            <span className="text-red-400 text-lg">⏰</span>
            <p className="text-sm font-semibold text-red-600">This notice expired on {expiresOn}.</p>
          </div>
        )}

        {/* Header */}
        <div className="flex items-start gap-4 mb-6">
          <div className="w-14 h-14 bg-indigo-50 rounded-2xl flex items-center justify-center text-3xl shrink-0">
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700 mb-2">
              {notice.category}
            </span>
            <h1 className="text-xl sm:text-2xl font-extrabold text-gray-900 leading-snug">
              {notice.title}
            </h1>
          </div>
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Category',  value: notice.category },
            { label: 'Year',      value: notice.year },
            { label: 'Class',     value: notice.class_name || 'All Classes' },
            { label: 'Published', value: publishedOn },
          ].map(m => (
            <div key={m.label} className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{m.label}</p>
              <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate">{m.value}</p>
            </div>
          ))}
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-4 mb-6 text-xs text-gray-400">
          {viewCount > 0 && (
            <span className="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              {viewCount.toLocaleString()} view{viewCount !== 1 ? 's' : ''}
            </span>
          )}
          {downloadCount > 0 && (
            <span className="flex items-center gap-1">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
              </svg>
              {downloadCount.toLocaleString()} download{downloadCount !== 1 ? 's' : ''}
            </span>
          )}
          {expiresOn && !isExpired && (
            <span className="flex items-center gap-1 text-amber-500">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Expires {expiresOn}
            </span>
          )}
        </div>

        {/* Description */}
        {notice.description && (
          <div className="bg-gray-50 rounded-2xl p-5 mb-6">
            <h2 className="text-sm font-bold text-gray-700 mb-2">About this Notice</h2>
            <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">{notice.description}</p>
          </div>
        )}

        {/* Action buttons */}
        {notice.public_url ? (
          <div className="flex flex-col sm:flex-row gap-3 mb-2">
            {/* View */}
            <a
              href={notice.public_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-6 py-3 rounded-xl transition-colors text-base flex-1 sm:flex-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View
            </a>

            {/* Download */}
            <button
              onClick={handleDownload}
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-800 font-semibold px-6 py-3 rounded-xl border border-gray-200 transition-colors text-base flex-1 sm:flex-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
              </svg>
              Download
            </button>

            {/* Share menu */}
            <ShareMenu title={notice.title} url={window.location.href} onDone={showToast} />
          </div>
        ) : (
          <div className="flex gap-3 mb-2">
            <ShareMenu title={notice.title} url={window.location.href} onDone={showToast} />
          </div>
        )}

        {/* No file notice */}
        {!notice.public_url && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mt-4 flex items-center gap-3">
            <span className="text-amber-500 text-xl shrink-0">⚠️</span>
            <p className="text-sm text-amber-700">File not yet uploaded. Check back soon.</p>
          </div>
        )}

        {/* YouTube embed — shown above file preview when a video URL exists */}
        {notice.youtube_url && (() => {
          const embedUrl = getYouTubeEmbedUrl(notice.youtube_url)
          if (!embedUrl) return null
          return (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-bold text-gray-700 flex items-center gap-2">
                  <span className="text-red-600">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                      <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
                    </svg>
                  </span>
                  Watch Explanation Video
                </h2>
                <a
                  href={notice.youtube_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
                    <path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z" />
                  </svg>
                  Watch on YouTube
                </a>
              </div>
              <div
                className="rounded-2xl overflow-hidden border border-gray-200 bg-black"
                style={{ position: 'relative', paddingTop: '56.25%' }}
              >
                <iframe
                  src={embedUrl}
                  title={`${notice.title} — YouTube Video`}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  style={{
                    position: 'absolute', top: 0, left: 0,
                    width: '100%', height: '100%', border: 'none',
                  }}
                />
              </div>
            </div>
          )
        })()}

        {/* File preview */}
        {notice.public_url && <FilePreview notice={notice} />}
      </div>

      {/* ── Related Notices ── */}
      {related.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              More {notice.category} Notices
            </h2>
            <Link
              to={`/official-notices?category=${encodeURIComponent(notice.category)}`}
              className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View all →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {related.map(n => <NoticeCard key={n.id} notice={n} />)}
          </div>
        </div>
      )}

      {/* Back link */}
      <div className="mt-8">
        <Link to="/official-notices" className="text-sm text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1">
          ← Back to Official Notices
        </Link>
      </div>
    </div>
  )
}
