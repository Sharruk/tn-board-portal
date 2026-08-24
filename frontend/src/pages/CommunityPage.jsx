import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import { getCommunityPosts, createCommunityPost } from '../services/community'

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export default function CommunityPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')

  // Create post modal state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newContent, setNewContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [modalError, setModalError] = useState(null)

  const fetchPosts = async (targetPage = 1) => {
    setLoading(true)
    setError(null)
    try {
      const res = await getCommunityPosts(targetPage, 15)
      setPosts(res.data || [])
      setTotal(res.total || 0)
      setHasNext(res.has_next || false)
      setPage(targetPage)
    } catch (err) {
      setError(err.message || 'Failed to load community discussions.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPosts(1)
  }, [])

  const handleStartDiscussion = () => {
    if (!isAuthenticated) {
      signInWithGoogle()
      return
    }
    setModalError(null)
    setIsModalOpen(true)
  }

  const handleCreatePost = async e => {
    e.preventDefault()
    if (!newTitle.trim() || !newContent.trim()) {
      setModalError('Title and content are required.')
      return
    }
    if (newTitle.trim().length < 3) {
      setModalError('Title must be at least 3 characters.')
      return
    }
    setSubmitting(true)
    setModalError(null)
    try {
      const created = await createCommunityPost({
        title: newTitle.trim(),
        content: newContent.trim(),
      })
      setIsModalOpen(false)
      setNewTitle('')
      setNewContent('')
      navigate(`/community/post/${created.id}`)
    } catch (err) {
      setModalError(err.message || 'Failed to create discussion topic.')
    } finally {
      setSubmitting(false)
    }
  }

  const filteredPosts = posts.filter(
    p =>
      p.title.toLowerCase().includes(search.toLowerCase()) ||
      p.author_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-8">

        {/* ── Hero ────────────────────────────────────────────────────── */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-3xl p-6 sm:p-10 text-white shadow-lg relative overflow-hidden">
          <div className="relative z-10 max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 backdrop-blur-sm text-xs font-semibold uppercase tracking-wider">
              <span>💬</span> Student &amp; Teacher Forum
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              Community Discussions
            </h1>
            <p className="text-blue-100 text-sm sm:text-base leading-relaxed">
              Ask questions, discuss previous year papers, share study notes, request specific answer keys, and prepare together.
            </p>
            <div className="pt-2 flex flex-wrap items-center gap-3">
              <button
                onClick={handleStartDiscussion}
                className="px-5 py-2.5 bg-white text-blue-700 hover:bg-blue-50 font-bold text-sm rounded-xl transition shadow-md flex items-center gap-2"
              >
                <span>✍️</span> Start a Discussion
              </button>
            </div>
          </div>
          <div className="absolute right-4 bottom-4 opacity-10 text-9xl select-none pointer-events-none hidden md:block">
            📚
          </div>
        </div>

        {/* ── Search & Filter Controls ─────────────────────────────────── */}
        <div className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <input
              type="text"
              placeholder="Search topics or authors…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded-xl pl-9 pr-3 py-2 outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
            />
            <span className="absolute left-3 top-2.5 text-gray-400 text-sm">🔍</span>
          </div>
          <div className="text-xs font-medium text-gray-500">
            Showing <strong className="text-gray-800">{filteredPosts.length}</strong> of{' '}
            <strong className="text-gray-800">{total}</strong> discussions
          </div>
        </div>

        {/* ── Discussion Feed ─────────────────────────────────────────── */}
        <div className="space-y-3">
          {loading ? (
            <div className="bg-white rounded-2xl border border-gray-200 py-20 flex flex-col items-center justify-center gap-3">
              <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
              <p className="text-sm font-medium text-gray-500">Loading discussions…</p>
            </div>
          ) : error ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center space-y-3">
              <p className="text-3xl">⚠️</p>
              <p className="text-sm font-semibold text-gray-800">Unable to load discussions</p>
              <p className="text-xs text-red-600">{error}</p>
              <button
                onClick={() => fetchPosts(page)}
                className="px-4 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-xl text-xs font-semibold transition"
              >
                Try Again
              </button>
            </div>
          ) : filteredPosts.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center space-y-3">
              <p className="text-4xl">💡</p>
              <h3 className="text-base font-bold text-gray-800">
                {search ? 'No matching discussions found' : 'No discussions yet'}
              </h3>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                {search
                  ? 'Try searching with different keywords.'
                  : 'Start the first conversation about exams, answer keys, or study materials!'}
              </p>
              <button
                onClick={handleStartDiscussion}
                className="inline-block mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition"
              >
                Start Discussion
              </button>
            </div>
          ) : (
            filteredPosts.map(post => (
              <Link
                key={post.id}
                to={`/community/post/${post.id}`}
                className="block bg-white hover:bg-blue-50/40 border border-gray-200 hover:border-blue-300 rounded-2xl p-5 transition-all shadow-sm group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {post.is_pinned && (
                        <span className="inline-flex items-center gap-1 bg-amber-100 text-amber-800 text-[11px] font-bold px-2.5 py-0.5 rounded-full">
                          📌 Pinned
                        </span>
                      )}
                      <h2 className="text-base font-bold text-gray-900 group-hover:text-blue-600 transition-colors truncate">
                        {post.title}
                      </h2>
                    </div>
                    <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed">
                      {post.content}
                    </p>
                    <div className="flex items-center gap-4 text-[11px] text-gray-400 pt-1">
                      <span className="font-medium text-gray-600">👤 {post.author_name}</span>
                      <span>📅 {fmtDate(post.created_at)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="flex flex-col items-center justify-center bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 min-w-[54px]">
                      <span className="text-xs font-bold text-gray-800">{post.reply_count}</span>
                      <span className="text-[10px] text-gray-500 font-medium">replies</span>
                    </div>
                    <div className="flex flex-col items-center justify-center bg-blue-50 border border-blue-100 rounded-xl px-3 py-1.5 min-w-[54px]">
                      <span className="text-xs font-bold text-blue-700">{post.upvotes}</span>
                      <span className="text-[10px] text-blue-600 font-medium">upvotes</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>

        {/* ── Pagination ──────────────────────────────────────────────── */}
        {!loading && total > 15 && (
          <div className="flex items-center justify-center gap-3 pt-4">
            <button
              onClick={() => fetchPosts(page - 1)}
              disabled={page <= 1}
              className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 transition"
            >
              ← Previous
            </button>
            <span className="text-xs text-gray-500 font-medium">Page {page}</span>
            <button
              onClick={() => fetchPosts(page + 1)}
              disabled={!hasNext}
              className="px-4 py-2 border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 transition"
            >
              Next →
            </button>
          </div>
        )}

      </div>

      {/* ── Create Post Modal ────────────────────────────────────────── */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setIsModalOpen(false)}
          />
          <div className="relative z-10 bg-white rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span>✍️</span> New Discussion Topic
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 p-1 rounded-lg transition text-lg leading-none"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreatePost} className="p-6 space-y-4 overflow-y-auto">
              {modalError && (
                <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-xs text-red-600">
                  {modalError}
                </div>
              )}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Topic Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  placeholder="e.g., Question 14 doubt in Class 12 Maths March 2024"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  maxLength={200}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Details / Body <span className="text-red-500">*</span>
                </label>
                <textarea
                  rows={5}
                  placeholder="Describe your question, share your solution notes, or explain what material you are looking for…"
                  value={newContent}
                  onChange={e => setNewContent(e.target.value)}
                  maxLength={5000}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  required
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 rounded-xl transition flex items-center justify-center gap-2"
                >
                  {submitting ? (
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  ) : (
                    '🚀 Post Topic'
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2.5 border border-gray-200 text-gray-600 hover:bg-gray-50 text-sm font-semibold rounded-xl transition"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
