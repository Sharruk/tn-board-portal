import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import {
  getCommunityPost,
  addCommunityComment,
  deleteCommunityComment,
  updateCommunityPost,
  deleteCommunityPost,
  togglePostUpvote,
  CATEGORY_ICONS,
} from '../services/community'
import UserProfileModal from '../components/UserProfileModal'
import ReportModal from '../components/ReportModal'
import UserAvatar from '../components/common/UserAvatar'

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

// Recursive Comment Component
function CommentItem({ comment, post, onReply, onDelete, onReport, onUserClick, currentUid, isAdmin }) {
  const [showReplyBox, setShowReplyBox] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [submittingReply, setSubmittingReply] = useState(false)

  const handleSendReply = async e => {
    e.preventDefault()
    if (!replyText.trim()) return
    setSubmittingReply(true)
    try {
      await onReply(comment.id, replyText.trim())
      setReplyText('')
      setShowReplyBox(false)
    } finally {
      setSubmittingReply(false)
    }
  }

  const isAuthor = currentUid && comment.firebase_uid === currentUid

  return (
    <div className="space-y-3">
      <div className="bg-white rounded-2xl border border-gray-200 p-4 sm:p-5 shadow-xs space-y-2.5 hover:border-gray-300 transition">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <UserAvatar
              src={comment.author_avatar}
              name={comment.author_name}
              size="xs"
            />
            <button
              type="button"
              onClick={() => onUserClick({ firebase_uid: comment.firebase_uid, author_name: comment.author_name })}
              className="font-bold text-gray-800 hover:text-blue-600 transition-colors"
            >
              {comment.author_name}
            </button>
            {comment.firebase_uid === post.firebase_uid && (
              <span className="text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5 rounded">
                Author
              </span>
            )}
          </div>
          <span className="text-gray-400 text-[11px]">{fmtDate(comment.created_at)}</span>
        </div>

        <p className="text-xs sm:text-sm text-gray-700 leading-relaxed whitespace-pre-wrap pl-9">
          {comment.content}
        </p>

        <div className="flex items-center justify-between pt-2 pl-9 text-xs text-gray-500 border-t border-gray-50">
          <button
            type="button"
            onClick={() => setShowReplyBox(!showReplyBox)}
            className="font-semibold text-blue-600 hover:text-blue-800 transition flex items-center gap-1"
          >
            <span>↩</span> Reply
          </button>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => onReport('comment', comment.id)}
              className="text-gray-400 hover:text-red-500 transition text-[11px]"
              title="Report reply"
            >
              🚩 Report
            </button>
            {(isAuthor || isAdmin) && (
              <button
                type="button"
                onClick={() => onDelete(comment.id)}
                className="text-gray-400 hover:text-red-600 transition text-[11px]"
                title="Delete reply"
              >
                🗑️ Delete
              </button>
            )}
          </div>
        </div>

        {/* Inline reply box */}
        {showReplyBox && (
          <form onSubmit={handleSendReply} className="pt-3 pl-9 space-y-2">
            <textarea
              rows={2}
              value={replyText}
              onChange={e => setReplyText(e.target.value)}
              placeholder={`Reply to ${comment.author_name}…`}
              className="w-full text-xs p-2.5 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowReplyBox(false)}
                className="px-3 py-1 text-xs text-gray-500 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingReply || !replyText.trim()}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg shadow-xs disabled:opacity-50"
              >
                {submittingReply ? 'Sending…' : 'Send Reply'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Nested Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="pl-6 sm:pl-10 space-y-3 border-l-2 border-blue-100">
          {comment.replies.map(reply => (
            <CommentItem
              key={reply.id}
              comment={reply}
              post={post}
              onReply={onReply}
              onDelete={onDelete}
              onReport={onReport}
              onUserClick={onUserClick}
              currentUid={currentUid}
              isAdmin={isAdmin}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function CommunityPostDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, isAuthenticated, isAdmin } = useAuth()

  const [post, setPost] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [commentText, setCommentText] = useState('')
  const [submittingComment, setSubmittingComment] = useState(false)
  const [commentError, setCommentError] = useState(null)
  const [upvoting, setUpvoting] = useState(false)

  // Report & Profile modal states
  const [reportTarget, setReportTarget] = useState(null)
  const [profileUser, setProfileUser] = useState(null)

  const fetchPost = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getCommunityPost(id)
      setPost(data)
      document.title = `${data.title} | Community | TN Board Portal`
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
      const { user: authedUser } = await signInWithGoogle()
      if (!authedUser) return
    }
    if (upvoting) return
    setUpvoting(true)
    try {
      const res = await togglePostUpvote(id)
      setPost(p => p ? { ...p, upvotes: res.upvotes, likes_count: res.upvotes } : null)
    } catch (err) {
      // ignore
    } finally {
      setUpvoting(false)
    }
  }

  const handleCommentSubmit = async (parentId = null, text = commentText) => {
    if (!text.trim()) return
    if (!isAuthenticated) {
      const { user: authedUser } = await signInWithGoogle()
      if (!authedUser) return
    }
    setSubmittingComment(true)
    setCommentError(null)
    try {
      await addCommunityComment(id, {
        content: text.trim(),
        parent_id: parentId,
        author_avatar: user?.photoURL || null,
      })
      setCommentText('')
      await fetchPost()
    } catch (err) {
      setCommentError(err.message || 'Failed to submit reply.')
    } finally {
      setSubmittingComment(false)
    }
  }

  const handleDeleteComment = async commentId => {
    if (!window.confirm('Delete this comment?')) return
    try {
      await deleteCommunityComment(commentId)
      await fetchPost()
    } catch (err) {
      alert(err.message || 'Failed to delete comment')
    }
  }

  const handleDeletePost = async () => {
    if (!window.confirm('Are you sure you want to delete this discussion topic?')) return
    try {
      await deleteCommunityPost(id)
      navigate('/community')
    } catch (err) {
      alert(err.message || 'Failed to delete post')
    }
  }

  const handleToggleResolved = async () => {
    if (!post) return
    const newStatus = post.status === 'resolved' ? 'open' : 'resolved'
    try {
      await updateCommunityPost(id, { status: newStatus })
      setPost(p => p ? { ...p, status: newStatus } : null)
    } catch (err) {
      alert(err.message || 'Failed to update topic status')
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

  const isPostAuthor = user && post.firebase_uid === user.uid

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      {profileUser && (
        <UserProfileModal
          uid={profileUser.firebase_uid}
          authorName={profileUser.author_name}
          onClose={() => setProfileUser(null)}
        />
      )}

      {reportTarget && (
        <ReportModal
          targetType={reportTarget.type}
          targetId={reportTarget.id}
          onClose={() => setReportTarget(null)}
          onSuccess={() => alert('Thank you. The report has been sent to moderators for review.')}
        />
      )}

      <div className="max-w-4xl mx-auto space-y-6">

        {/* ── Breadcrumb ──────────────────────────────────────────────── */}
        <div className="flex items-center justify-between text-xs text-gray-500 font-medium">
          <div className="flex items-center gap-2">
            <Link to="/community" className="hover:text-blue-600 transition">
              ← Discussions
            </Link>
            <span>/</span>
            <span className="text-gray-800 truncate max-w-xs sm:max-w-md">{post.title}</span>
          </div>
          <button
            onClick={() => setReportTarget({ type: 'post', id: post.id })}
            className="text-gray-400 hover:text-red-500 transition text-[11px] flex items-center gap-1"
          >
            <span>🚩</span> Report Topic
          </button>
        </div>

        {/* ── Main Post Card ──────────────────────────────────────────── */}
        <div className="bg-white rounded-3xl border border-gray-200 p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                {post.is_pinned && (
                  <span className="bg-amber-100 text-amber-800 text-[11px] font-bold px-2.5 py-0.5 rounded-full">
                    📌 Pinned
                  </span>
                )}
                <span className="bg-gray-100 text-gray-700 text-[11px] font-bold px-2.5 py-0.5 rounded-md border border-gray-200">
                  {CATEGORY_ICONS[post.category] || '💬'} {post.category || 'Discussion'}
                </span>
                {post.status && post.status !== 'open' && (
                  <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-bold px-2.5 py-0.5 rounded-md">
                    ✓ {post.status.toUpperCase()}
                  </span>
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-gray-900 leading-tight">
                {post.title}
              </h1>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <button
                  type="button"
                  onClick={() => setProfileUser({ firebase_uid: post.firebase_uid, author_name: post.author_name })}
                  className="font-semibold text-gray-700 hover:text-blue-600 transition flex items-center gap-1.5"
                >
                  <UserAvatar
                    src={post.author_avatar}
                    name={post.author_name}
                    size="xs"
                  />
                  {post.author_name}
                </button>
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
              <span className="text-xs font-extrabold">{post.upvotes ?? post.likes_count ?? 0}</span>
            </button>
          </div>

          <div className="text-sm sm:text-base text-gray-700 leading-relaxed whitespace-pre-wrap pt-2 border-t border-gray-100">
            {post.content}
          </div>

          {/* Author/Admin Actions */}
          {(isPostAuthor || isAdmin) && (
            <div className="flex items-center justify-end gap-2 pt-4 border-t border-gray-100">
              <button
                onClick={handleToggleResolved}
                className="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-xl border border-emerald-200 transition"
              >
                {post.status === 'resolved' ? 'Mark as Open' : '✓ Mark as Resolved'}
              </button>
              <button
                onClick={handleDeletePost}
                className="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 text-xs font-semibold rounded-xl border border-red-200 transition"
              >
                🗑️ Delete Topic
              </button>
            </div>
          )}
        </div>

        {/* ── Comments / Threaded Replies Section ─────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <span>💬</span> Discussion Replies ({post.comments?.length || 0})
            </h2>
          </div>

          {/* Comment Box */}
          <div className="bg-white rounded-3xl border border-gray-200 p-5 shadow-sm">
            {isAuthenticated ? (
              <form onSubmit={e => { e.preventDefault(); handleCommentSubmit() }} className="space-y-3">
                {/* Authenticated Identity Context */}
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-2xl border border-gray-100">
                  <UserAvatar user={user} size="sm" />
                  <div className="text-xs">
                    <span className="font-semibold text-gray-800">{user?.displayName || user?.email?.split('@')[0] || 'Community Member'}</span>
                    <span className="text-gray-400 mx-1.5">·</span>
                    <span className="text-gray-500">{user?.email}</span>
                  </div>
                </div>

                {commentError && (
                  <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2 text-xs text-red-600">
                    {commentError}
                  </div>
                )}
                <textarea
                  rows={3}
                  placeholder="Write a helpful answer, share a solution hint, or add your insights…"
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
                    className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition flex items-center gap-2 shadow-sm"
                  >
                    {submittingComment ? <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '💬 Post Reply'}
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
                  className="px-5 py-2.5 bg-white border border-gray-200 hover:bg-gray-50 text-gray-800 text-xs font-semibold rounded-xl transition shadow-sm inline-flex items-center gap-2"
                >
                  <span>🔐</span> Sign in with Google to Reply
                </button>
              </div>
            )}
          </div>

          {/* Threaded Comments List */}
          {post.comments?.length === 0 ? (
            <div className="bg-white rounded-3xl border border-gray-200 p-8 text-center text-xs text-gray-400">
              No replies yet. Be the first to leave a comment!
            </div>
          ) : (
            <div className="space-y-4">
              {post.comments.map(comment => (
                <CommentItem
                  key={comment.id}
                  comment={comment}
                  post={post}
                  onReply={(parentId, text) => handleCommentSubmit(parentId, text)}
                  onDelete={handleDeleteComment}
                  onReport={(type, targetId) => setReportTarget({ type, id: targetId })}
                  onUserClick={u => setProfileUser(u)}
                  currentUid={user?.uid}
                  isAdmin={isAdmin}
                />
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
