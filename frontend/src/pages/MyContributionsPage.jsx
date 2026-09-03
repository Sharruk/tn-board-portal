import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import { getMySubmissions } from '../services/submissions'

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function formatBytes(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function MyContributionsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const [submissions, setSubmissions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('ALL')

  const fetchSubmissions = async () => {
    if (!isAuthenticated) return
    setLoading(true)
    setError(null)
    try {
      const res = await getMySubmissions()
      setSubmissions(res.data || [])
    } catch (err) {
      setError(err.message || 'Failed to load your contributions.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    document.title = 'My Contributions | TN Board Portal'
    if (isAuthenticated) {
      fetchSubmissions()
    }
  }, [isAuthenticated])

  if (authLoading) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm font-medium text-gray-500">Loading your contributions…</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4 py-16">
        <div className="max-w-md w-full text-center bg-white border border-gray-200 rounded-3xl p-8 shadow-sm">
          <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-5 text-2xl font-bold">
            📂
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900 mb-2">My Contributions</h1>
          <p className="text-gray-600 text-sm leading-relaxed mb-6">
            Sign in with Google to view and track all the question papers and answer keys you have submitted.
          </p>
          <button
            onClick={signInWithGoogle}
            className="w-full inline-flex items-center justify-center gap-3 bg-white hover:bg-gray-50 border border-gray-200 text-gray-800 font-semibold px-6 py-3.5 rounded-xl transition-all text-sm shadow-xs"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
            </svg>
            Sign in with Google
          </button>
        </div>
      </div>
    )
  }

  const filtered = submissions.filter(item => {
    if (statusFilter === 'ALL') return true
    return item.status.toLowerCase() === statusFilter.toLowerCase()
  })

  return (
    <div className="min-h-screen bg-gray-50/70 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* ── Breadcrumb & Header ────────────────────────────────────── */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Link to="/" className="hover:text-blue-600 transition">Home</Link>
              <span>/</span>
              <Link to="/profile" className="hover:text-blue-600 transition">Profile</Link>
              <span>/</span>
              <span className="text-gray-900 font-medium">My Contributions</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900">
              My Submissions &amp; Contributions
            </h1>
          </div>

          <Link
            to="/submit-material"
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition shadow-xs"
          >
            <span>📤</span> Submit New Material
          </Link>
        </div>

        {/* ── Filter Tabs ───────────────────────────────────────────── */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {[
            { key: 'ALL', label: `All (${submissions.length})` },
            { key: 'pending', label: `🟡 Under Review (${submissions.filter(s => s.status === 'pending').length})` },
            { key: 'approved', label: `🟢 Published (${submissions.filter(s => s.status === 'approved').length})` },
            { key: 'rejected', label: `🔴 Rejected (${submissions.filter(s => s.status === 'rejected').length})` },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setStatusFilter(tab.key)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition shrink-0 ${
                statusFilter === tab.key
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Submissions List ──────────────────────────────────────── */}
        {loading ? (
          <div className="bg-white rounded-3xl border border-gray-200 py-20 flex flex-col items-center justify-center gap-3">
            <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
            <p className="text-sm font-medium text-gray-500">Loading your submissions…</p>
          </div>
        ) : error ? (
          <div className="bg-white rounded-3xl border border-gray-200 p-8 text-center space-y-3">
            <p className="text-3xl">⚠️</p>
            <p className="text-sm font-semibold text-gray-800">Unable to load submissions</p>
            <p className="text-xs text-red-600">{error}</p>
            <button
              onClick={fetchSubmissions}
              className="px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-xl text-xs font-semibold"
            >
              Try Again
            </button>
          </div>
        ) : submissions.length === 0 ? (
          <div className="bg-white rounded-3xl border border-gray-200 p-12 text-center space-y-4 shadow-xs">
            <div className="w-16 h-16 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center text-3xl mx-auto">
              📚
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-bold text-gray-900">No submissions yet</h2>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                Help Tamil Nadu students by sharing question papers, mid term tests, and answer keys.
              </p>
            </div>
            <Link
              to="/submit-material"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition shadow-xs"
            >
              <span>📤</span> Submit Your First Material
            </Link>
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white rounded-3xl border border-gray-200 p-10 text-center space-y-2 shadow-xs">
            <p className="text-2xl">🔍</p>
            <h2 className="text-sm font-bold text-gray-800">No submissions in this filter</h2>
            <button
              onClick={() => setStatusFilter('ALL')}
              className="text-xs font-semibold text-blue-600 hover:underline"
            >
              View all submissions
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map(sub => {
              const isApproved = sub.status === 'approved'
              const isPending = sub.status === 'pending'
              const isRejected = sub.status === 'rejected'

              return (
                <div
                  key={sub.id}
                  className="bg-white rounded-3xl border border-gray-200/90 p-5 sm:p-6 shadow-xs space-y-4 hover:border-gray-300 transition"
                >
                  {/* Card Header: Details & Status */}
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-bold text-gray-800">
                          Submitted by: <strong className="text-blue-600">{sub.publisher_name}</strong>
                        </span>
                        <span className="text-gray-300">·</span>
                        <span className="text-xs text-gray-400">📅 {fmtDate(sub.created_at)}</span>
                      </div>
                      {sub.details && (
                        <p className="text-xs sm:text-sm text-gray-700 font-medium leading-relaxed pt-1">
                          {sub.details}
                        </p>
                      )}
                    </div>

                    {/* Status Badge */}
                    <div className="shrink-0">
                      {isPending && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-full text-xs font-bold">
                          <span>🟡</span> Under Review
                        </span>
                      )}
                      {isApproved && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-full text-xs font-bold">
                          <span>🟢</span> Published
                        </span>
                      )}
                      {isRejected && (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-red-50 text-red-800 border border-red-200 rounded-full text-xs font-bold">
                          <span>🔴</span> Rejected
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Attached Files List */}
                  {sub.files && sub.files.length > 0 && (
                    <div className="bg-gray-50/80 rounded-2xl p-3.5 border border-gray-100 space-y-2">
                      <p className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                        Attached Files ({sub.files.length}):
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {sub.files.map((f) => (
                          <div
                            key={f.id}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-gray-200 text-xs text-gray-700 font-medium shadow-2xs"
                          >
                            <span>📄</span>
                            <span className="truncate max-w-[200px] font-semibold">{f.original_filename}</span>
                            {f.file_size > 0 && (
                              <span className="text-[10px] text-gray-400">({formatBytes(f.file_size)})</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Published Papers Section (If approved) */}
                  {isApproved && (
                    <div className="bg-emerald-50/70 rounded-2xl p-4 border border-emerald-200 text-xs space-y-3">
                      {/* Thank-You Message Banner */}
                      <div className="bg-white/90 border border-emerald-200/80 rounded-xl p-3.5 space-y-1 shadow-2xs">
                        <p className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                          <span>🎉</span> Contribution Approved!
                        </p>
                        <p className="text-xs text-emerald-800 leading-relaxed whitespace-pre-line font-medium">
                          {sub.thank_you_message || "🎉 Your contribution is now public!\nThank you for contributing to the TN Board community. Your contribution may help another student prepare better. ❤️"}
                        </p>
                      </div>

                      {/* Published Papers Links */}
                      {sub.published_papers && sub.published_papers.length > 0 && (
                        <div className="divide-y divide-emerald-100/80 pt-1">
                          {sub.published_papers.map((paper) => (
                            <div key={paper.id} className="pt-2 first:pt-0 flex items-center justify-between gap-3 flex-wrap">
                              <div>
                                <p className="text-xs font-bold text-gray-900">{paper.title}</p>
                                <p className="text-[11px] text-emerald-700">
                                  {[paper.class_name, paper.subject_name, paper.exam_type, paper.year].filter(Boolean).join(' • ')}
                                </p>
                              </div>
                              <Link
                                to={`/paper/${paper.id}`}
                                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition shadow-2xs"
                              >
                                <span>📄</span> View Published Paper ↗
                              </Link>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Rejected Reason Banner (If rejected) */}
                  {isRejected && (
                    <div className="bg-red-50 rounded-2xl p-4 border border-red-200 text-xs text-red-800 space-y-1.5">
                      <p className="font-bold flex items-center gap-1.5 text-red-900">
                        <span>⚠️</span> Submission Status: Rejected
                      </p>
                      <p className="text-xs text-red-700 leading-relaxed whitespace-pre-line font-medium">
                        {sub.rejection_reason || 'The material could not be approved due to quality, syllabus alignment, or duplicate content.'}
                      </p>
                    </div>
                  )}


                  {/* Under Review Notice (If pending) */}
                  {isPending && (
                    <div className="bg-amber-50/60 rounded-2xl p-3.5 border border-amber-100 text-xs text-amber-800 flex items-center gap-2">
                      <span>⏳</span>
                      <span>Your material is in the review queue. Once approved by our team, it will appear publicly with your contribution name.</span>
                    </div>
                  )}

                </div>
              )
            })}
          </div>
        )}

      </div>
    </div>
  )
}
