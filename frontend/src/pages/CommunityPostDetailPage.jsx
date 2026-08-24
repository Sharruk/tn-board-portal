import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import {
  getCommunityPost,
  addCommunityComment,
  togglePostUpvote,
} from '../services/community'

function fmtDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function CommunityPostDetailPage() {
  const { id } = useParams()
  const { isAuthenticated } = useAuth()
  const [post, setPost] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [commentText, setCommentText] = useState('')
  const [submittingComment, setSubmittingComment] = useState(false)
  const [commentError, setCommentError] = useState(null)
  const [upvoting, setUpvoting] = useState(false)

  const fetchPost = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getCommunityPost(id)
      setPost(data)
    } catch (err) {
      setError(err.message || 'Discussion not found or failed to load.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPost()
  }, [id])

  const handleUpvote = async () => {
    if (!isAuthenticated) {
      signInWithGoogle()
      return
    }
    if (upvoting) return
    setUpvoting(true)
    try {
      const res = await togglePostUpvote(id)
      setPost(p => p ? { ...p, upvotes: res.upvotes } : null)
    } catch (err) {
      // ignore or alert
    } finally {
      setUpvoting(false)
    }
  }

  const handleCommentSubmit = async e => {
    e.preventDefault()
    if (!commentText.trim()) return
    setSubmittingComment(true)
    setCommentError(null)
    try {
      const newComment = await addCommunityComment(id, {
        content: commentText.trim(),
      })
      setPost(p => (p ? { ...p, comments: [...p.comments, newComment], reply_count: p.reply_count + 1 } : null))
      setCommentText('')
    } catch (err) {
      setCommentError(err.message || 'Failed to submit reply.')
    } finally {
      setSubmittingComment(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-20 flex flex-col items-center justify-center gap-3">
        <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
        <p className="text-sm font-medium text-gray-500">Loading discussion…</p>
      </div>
    )
  }

  if (error || !post) {
    return (
      <div className="min-h-[70vh] bg-gray-50 py-16 px-4 flex items-center justify-center">
        <div className="bg-white rounded-3xl border border-gray-200 p-8 max-w-md w-full text-center space-y-4 shadow-sm">
          <p className="text-4xl">🔍</p>
          <h2 className="text-lg font-bold text-gray-900">Discussion Not Found</h2>
          <p className="text-xs text-gray-500">{error || 'This discussion may have been removed or does not exist.'}</p>
          <Link
            to="/community"
            className="inline-block px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold transition"
          >
            ← Back to Discussions
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* ── Breadcrumb ──────────────────────────────────────────────── */}
        <div className="flex items-center gap-2 text-xs text-gray-500 font-medium">
          <Link to="/community" className="hover:text-blue-600 transition">
            ← Discussions
          </Link>
          <span>/</span>
          <span className="text-gray-800 truncate max-w-md">{post.title}</span>
        </div>

        {/* ── Main Post Card ──────────────────────────────────────────── */}
        <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                {post.is_pinned && (
                  <span className="bg-amber-100 text-amber-800 text-[11px] font-bold px-2.5 py-0.5 rounded-full">
                    📌 Pinned
                  </span>
                )}
                <h1 className="text-2xl font-extrabold text-gray-900 leading-tight">
                  {post.title}
                </h1>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span className="font-semibold text-gray-700">👤 {post.author_name}</span>
                <span>•</span>
                <span>📅 {fmtDate(post.created_at)}</span>
              </div>
            </div>
            <button
              onClick={handleUpvote}
              disabled={upvoting}
              className="flex flex-col items-center justify-center bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 px-4 py-2.5 rounded-2xl transition shrink-0 group shadow-sm"
              title="Upvote discussion"
            >
              <span className="text-base group-hover:-translate-y-0.5 transition-transform">▲</span>
              <span className="text-xs font-extrabold">{post.upvotes}</span>
            </button>
          </div>

          <div className="text-sm sm:text-base text-gray-700 leading-relaxed whitespace-pre-wrap pt-2 border-t border-gray-100">
            {post.content}
          </div>
        </div>

        {/* ── Comments / Replies Section ──────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <span>💬</span> Replies ({post.comments?.length || 0})
            </h2>
          </div>

          {/* Comment Form */}
          <div className="bg-white rounded-3xl border border-gray-200 p-5 shadow-sm">
            {isAuthenticated ? (
              <form onSubmit={handleCommentSubmit} className="space-y-3">
                {commentError && (
                  <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2 text-xs text-red-600">
                    {commentError}
                  </div>
                )}
                <textarea
                  rows={3}
                  placeholder="Write a helpful answer, share a solution, or add to the discussion…"
                  value={commentText}
                  onChange={e => setCommentText(e.target.value)}
                  maxLength={2000}
                  className="w-full text-sm border border-gray-200 rounded-2xl p-3.5 outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  required
                />
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={submittingComment || !commentText.trim()}
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition flex items-center gap-2 shadow-sm"
                  >
                    {submittingComment ? (
                      <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    ) : (
                      '💬 Post Reply'
                    )}
                  </button>
                </div>
              </form>
            ) : (
              <div className="text-center py-6 space-y-3">
                <p className="text-xs text-gray-500 font-medium">
                  Sign in with Google to reply or join this discussion.
                </p>
                <button
                  onClick={signInWithGoogle}
                  className="px-5 py-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold rounded-xl transition shadow-sm inline-flex items-center gap-2"
                >
                  <span>🔐</span> Sign in to Reply
                </button>
              </div>
            )}
          </div>

          {/* Comments List */}
          {post.comments?.length === 0 ? (
            <div className="bg-white rounded-3xl border border-gray-200 p-8 text-center text-xs text-gray-400">
              No replies yet. Be the first to leave a comment!
            </div>
          ) : (
            <div className="space-y-3">
              {post.comments.map(comment => (
                <div
                  key={comment.id}
                  className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-[10px] flex items-center justify-center">
                        {comment.author_name.charAt(0).toUpperCase()}
                      </div>
                      <span className="font-bold text-gray-800">{comment.author_name}</span>
                    </div>
                    <span className="text-gray-400 text-[11px]">{fmtDate(comment.created_at)}</span>
                  </div>
                  <p className="text-xs sm:text-sm text-gray-700 leading-relaxed whitespace-pre-wrap pl-8">
                    {comment.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
