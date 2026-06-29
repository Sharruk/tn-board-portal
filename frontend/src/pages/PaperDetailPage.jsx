import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import PaperCard from '../components/PaperCard'
import { getPaper, getPaperBySlug, recordDownload } from '../services/papers'
import { getPapersForSubject } from '../services/subjects'
import { downloadPaper, viewPdf } from '../utils/download'

function YoutubeEmbed({ url }) {
  const getVideoId = (url) => {
    if (!url) return null
    try {
      const u = new URL(url)
      // youtu.be short links  →  https://youtu.be/VIDEO_ID
      if (u.hostname === 'youtu.be') return u.pathname.slice(1).split('?')[0]
      // All youtube.com variants (www, m, music, …)
      if (u.hostname.includes('youtube.com')) {
        // Shorts  →  /shorts/VIDEO_ID
        const shortsMatch = u.pathname.match(/\/shorts\/([A-Za-z0-9_-]{11})/)
        if (shortsMatch) return shortsMatch[1]
        // Embed   →  /embed/VIDEO_ID
        const embedMatch = u.pathname.match(/\/embed\/([A-Za-z0-9_-]{11})/)
        if (embedMatch) return embedMatch[1]
        // Standard watch  →  ?v=VIDEO_ID
        return u.searchParams.get('v')
      }
    } catch {
      // Fallback regex covering watch?v=, youtu.be/, and /shorts/
      const m = url.match(/(?:v=|youtu\.be\/|shorts\/)([A-Za-z0-9_-]{11})/)
      return m ? m[1] : null
    }
    return null
  }
  const videoId = getVideoId(url)
  if (!videoId) return null
  return (
    <div className="rounded-2xl overflow-hidden aspect-video bg-black shadow-lg">
      <iframe
        src={`https://www.youtube.com/embed/${videoId}`}
        title="Explanation Video"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
        className="w-full h-full"
      />
    </div>
  )
}

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

export default function PaperDetailPage() {
  const { id } = useParams()
  const [paper, setPaper] = useState(null)
  const [related, setRelated] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [downloadCount, setDownloadCount] = useState(0)

  const showToast = useCallback((msg) => setToast(msg), [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    // Support both numeric IDs ("/paper/5") and slug URLs ("/paper/class-10-maths-2024-5")
    const isNumeric = /^\d+$/.test(id)
    const fetchFn = isNumeric ? getPaper(id) : getPaperBySlug(id)

    fetchFn
      .then(res => {
        const p = res.data
        setPaper(p)
        setDownloadCount(p.download_count ?? 0)
        if (p.subject_id) {
          getPapersForSubject(p.subject_id)
            .then(r => setRelated(r.data.filter(rp => rp.id !== p.id).slice(0, 4)))
            .catch(() => {})
        }
      })
      .catch(err => setError(err.message || 'Paper not found'))
      .finally(() => setLoading(false))
  }, [id])

  const handleDownload = useCallback(() => {
    if (!paper) return
    recordDownload(paper.id)
      .then(() => setDownloadCount(c => c + 1))
      .catch(() => {})
    // Pass original_filename so the blob-download uses the correct filename.
    // Falls back to paper.title + ".pdf" for pre-migration papers (original_filename = null).
    downloadPaper(paper.public_url, paper.title, paper.original_filename)
  }, [paper])


  const handleShare = useCallback(async () => {
    const url = window.location.href
    const shareData = {
      title: paper?.title ?? 'TN Board Paper',
      text: `Check out this TN State Board paper: ${paper?.title}`,
      url,
    }
    if (navigator.share) {
      try {
        await navigator.share(shareData)
        showToast('Shared successfully!')
      } catch {
        // user cancelled
      }
    } else {
      try {
        await navigator.clipboard.writeText(url)
        showToast('Link copied to clipboard!')
      } catch {
        showToast('Copy this link: ' + url)
      }
    }
  }, [paper, showToast])

  if (loading) return <div className="max-w-4xl mx-auto px-4 py-12"><LoadingSpinner text="Loading paper…" /></div>
  if (error) return <div className="max-w-4xl mx-auto px-4 py-12"><ErrorMessage message={error} /></div>
  if (!paper) return null

  const isQuestion = paper.paper_type === 'question'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Toast */}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}

      {/* Breadcrumb */}
      {paper.subjects && (
        <Breadcrumb items={[
          { label: 'Home', href: '/' },
          { label: paper.subjects.classes?.name || 'Class', href: `/class/${paper.subjects.class_id}` },
          { label: paper.subjects.name, href: `/subject/${paper.subject_id}` },
          { label: paper.exam_type, href: `/papers?subject_id=${paper.subject_id}&exam_type=${encodeURIComponent(paper.exam_type)}` },
          { label: paper.title },
        ]} />
      )}

      <div className="mt-6 card p-6 sm:p-8">
        {/* Header */}
        <div className="flex items-start gap-4 mb-6">
          <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center shrink-0 text-2xl">
            {isQuestion ? '📄' : '✅'}
          </div>
          <div className="flex-1 min-w-0">
            <span className={`badge text-xs ${isQuestion ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
              {isQuestion ? 'Question Paper' : 'Answer Key'}
            </span>
            <h1 className="text-xl sm:text-2xl font-extrabold text-gray-900 mt-2 leading-snug">{paper.title}</h1>
          </div>
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[
            { label: 'Class',     value: paper.subjects?.classes?.name || '—' },
            { label: 'Subject',   value: paper.subjects?.name || '—' },
            { label: 'Exam Type', value: paper.exam_type },
            { label: 'Year',      value: paper.year },
          ].map(m => (
            <div key={m.label} className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{m.label}</p>
              <p className="text-sm font-semibold text-gray-800 mt-0.5">{m.value}</p>
            </div>
          ))}
        </div>

        {/* ── Action buttons ── */}
        {paper.public_url ? (
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            {/* View PDF — opened via blob: URL to hide the Supabase UUID */}
            <button
              onClick={() => viewPdf(paper.public_url, paper.title, paper.original_filename)}
              className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold px-6 py-3 rounded-xl transition-colors text-base flex-1 sm:flex-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View Paper
            </button>

            {/* Download PDF */}
            <button
              onClick={handleDownload}
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 active:bg-gray-100 text-gray-800 font-semibold px-6 py-3 rounded-xl border border-gray-200 transition-colors text-base flex-1 sm:flex-none"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
              </svg>
              {isQuestion ? 'Download Question Paper' : 'Download Answer Key'}
            </button>

            {/* Share */}
            <button
              onClick={handleShare}
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 active:bg-gray-100 text-gray-600 font-semibold px-4 py-3 rounded-xl border border-gray-200 transition-colors text-base sm:flex-none"
              title="Share this paper"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              <span className="hidden sm:inline">Share</span>
            </button>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <button
              onClick={handleShare}
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-600 font-semibold px-5 py-3 rounded-xl border border-gray-200 transition-colors text-base"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              Share
            </button>
          </div>
        )}

        {/* Download count */}
        {downloadCount > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-6 -mt-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
            </svg>
            <span>{downloadCount.toLocaleString()} download{downloadCount !== 1 ? 's' : ''}</span>
          </div>
        )}

        {/* No PDF notice */}
        {!paper.public_url && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-6 flex items-center gap-3">
            <span className="text-amber-500 text-xl shrink-0">⚠️</span>
            <p className="text-sm text-amber-700">PDF file not yet uploaded. Check back soon.</p>
          </div>
        )}

        {/* Full empty state */}
        {!paper.public_url && !paper.youtube_url && (
          <div className="bg-gray-50 border border-gray-200 rounded-2xl px-6 py-10 mb-6 flex flex-col items-center text-center">
            <span className="text-5xl mb-4">📭</span>
            <h3 className="font-bold text-gray-700 text-lg mb-1">Content coming soon</h3>
            <p className="text-sm text-gray-500 max-w-sm">
              The PDF and explanation video for this paper haven't been added yet. Please check back later.
            </p>
          </div>
        )}

        {/* YouTube embed */}
        {paper.youtube_url && (
          <div className="mt-2">
            <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="text-red-500">▶</span> Explanation Video
            </h2>
            <YoutubeEmbed url={paper.youtube_url} />
          </div>
        )}
      </div>

      {/* ── Related Papers ── */}
      {related.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              More from {paper.subjects?.name || 'this subject'}
            </h2>
            <Link
              to={`/subject/${paper.subject_id}`}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              View all →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {related.map(p => <PaperCard key={p.id} paper={p} />)}
          </div>
        </div>
      )}

      {/* Back link */}
      <div className="mt-8">
        <Link to={`/subject/${paper.subject_id}`} className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
          ← Back to {paper.subjects?.name || 'Subject'}
        </Link>
      </div>
    </div>
  )
}
