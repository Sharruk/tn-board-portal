import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import PaperCard from '../components/PaperCard'
import { getPaper } from '../services/papers'
import { getPapersForSubject } from '../services/subjects'

function YoutubeEmbed({ url }) {
  const getVideoId = (url) => {
    if (!url) return null
    const patterns = [
      /youtu\.be\/([^?&]+)/,
      /youtube\.com\/watch\?v=([^&]+)/,
      /youtube\.com\/embed\/([^?&]+)/,
    ]
    for (const p of patterns) {
      const m = url.match(p)
      if (m) return m[1]
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

function DownloadButton({ href, label, variant = 'primary' }) {
  if (!href) return null
  const styles = variant === 'primary'
    ? 'btn-primary text-base px-8 py-3.5 w-full sm:w-auto justify-center'
    : 'btn-secondary text-base px-8 py-3.5 w-full sm:w-auto justify-center'
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={styles}>
      <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
      </svg>
      {label}
    </a>
  )
}

export default function PaperDetailPage() {
  const { id } = useParams()
  const [paper, setPaper] = useState(null)
  const [related, setRelated] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getPaper(id)
      .then(res => {
        const p = res.data
        setPaper(p)
        if (p.subject_id) {
          getPapersForSubject(p.subject_id, { exam_type: p.exam_type })
            .then(r => setRelated(r.data.filter(rp => rp.id !== p.id).slice(0, 3)))
            .catch(() => {})
        }
      })
      .catch(err => setError(err.response?.data?.detail || 'Paper not found'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="max-w-4xl mx-auto px-4 py-12"><LoadingSpinner text="Loading paper…" /></div>
  if (error) return <div className="max-w-4xl mx-auto px-4 py-12"><ErrorMessage message={error} /></div>
  if (!paper) return null

  const isQuestion = paper.paper_type === 'question'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {paper.subject && (
        <Breadcrumb items={[
          { label: 'Home', href: '/' },
          { label: paper.subject.class_name || 'Class', href: `/class/${paper.subject.class_id}` },
          { label: paper.subject.name, href: `/subject/${paper.subject_id}` },
          { label: paper.exam_type, href: `/papers?subject_id=${paper.subject_id}&exam_type=${encodeURIComponent(paper.exam_type)}` },
          { label: paper.title },
        ]} />
      )}

      <div className="mt-6 card p-8">
        {/* Header */}
        <div className="flex items-start gap-4 mb-6">
          <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center shrink-0 text-2xl">
            {isQuestion ? '📄' : '✅'}
          </div>
          <div>
            <span className={`badge text-xs ${isQuestion ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
              {isQuestion ? 'Question Paper' : 'Answer Key'}
            </span>
            <h1 className="text-2xl font-extrabold text-gray-900 mt-2 leading-snug">{paper.title}</h1>
          </div>
        </div>

        {/* Meta */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[
            { label: 'Class', value: paper.subject?.class_name || '—' },
            { label: 'Subject', value: paper.subject?.name || '—' },
            { label: 'Exam Type', value: paper.exam_type },
            { label: 'Year', value: paper.year },
          ].map(m => (
            <div key={m.label} className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{m.label}</p>
              <p className="text-sm font-semibold text-gray-800 mt-0.5">{m.value}</p>
            </div>
          ))}
        </div>

        {/* Download buttons */}
        <div className="flex flex-col sm:flex-row gap-3 mb-8">
          {isQuestion ? (
            <>
              <DownloadButton href={paper.public_url} label="Download Question Paper" variant="primary" />
            </>
          ) : (
            <DownloadButton href={paper.public_url} label="Download Answer Key" variant="secondary" />
          )}
        </div>

        {/* No file notice */}
        {!paper.public_url && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 mb-8 flex items-center gap-3">
            <span className="text-amber-500 text-xl">⚠️</span>
            <p className="text-sm text-amber-700">PDF file not yet uploaded. Check back soon.</p>
          </div>
        )}

        {/* Empty state — no PDF and no YouTube */}
        {!paper.public_url && !paper.youtube_url && (
          <div className="bg-gray-50 border border-gray-200 rounded-2xl px-6 py-10 mb-8 flex flex-col items-center text-center">
            <span className="text-5xl mb-4">📭</span>
            <h3 className="font-bold text-gray-700 text-lg mb-1">Content coming soon</h3>
            <p className="text-sm text-gray-500 max-w-sm">
              The PDF and explanation video for this paper haven't been added yet. Please check back later or visit our YouTube channel.
            </p>
          </div>
        )}

        {/* YouTube embed */}
        {paper.youtube_url && (
          <div className="mb-2">
            <h2 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span className="text-red-500">▶</span> Explanation Video
            </h2>
            <YoutubeEmbed url={paper.youtube_url} />
          </div>
        )}
      </div>

      {/* Related papers */}
      {related.length > 0 && (
        <div className="mt-10">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Related Papers</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {related.map(p => <PaperCard key={p.id} paper={p} />)}
          </div>
        </div>
      )}

      <div className="mt-8">
        <Link to={`/subject/${paper.subject_id}`} className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
          ← Back to {paper.subject?.name || 'Subject'}
        </Link>
      </div>
    </div>
  )
}
