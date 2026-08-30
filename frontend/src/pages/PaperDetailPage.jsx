import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import PaperCard from '../components/PaperCard'
import {
  getPaper,
  getPaperBySlug,
  recordDownload,
  getPaperLikes,
  togglePaperLike,
  getPaperComments,
  addPaperComment,
  deletePaperComment,
} from '../services/papers'
import { getPapersForSubject } from '../services/subjects'
import { downloadPaper, viewPdf } from '../utils/download'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'
import { trackPaperView, trackDownload } from '../services/analytics'
import ReportModal from '../components/ReportModal'
import UserProfileModal from '../components/UserProfileModal'

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

function YoutubeEmbed({ url }) {
  const getVideoId = (url) => {
    if (!url) return null
    try {
      const u = new URL(url)
      if (u.hostname === 'youtu.be') return u.pathname.slice(1).split('?')[0]
      if (u.hostname.includes('youtube.com')) {
        const shortsMatch = u.pathname.match(/\/shorts\/([A-Za-z0-9_-]{11})/)
        if (shortsMatch) return shortsMatch[1]
        const embedMatch = u.pathname.match(/\/embed\/([A-Za-z0-9_-]{11})/)
        if (embedMatch) return embedMatch[1]
        return u.searchParams.get('v')
      }
    } catch {
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

// Threaded Comment Card Component
function PaperCommentItem({ comment, onReply, onDelete, onReport, onUserClick, currentUid, isAdmin }) {
  const [showReplyBox, setShowReplyBox] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSendReply = async (e) => {
    e.preventDefault()
    if (!replyText.trim()) return
    setSubmitting(true)
    try {
      await onReply(comment.id, replyText.trim())
      setReplyText('')
      setShowReplyBox(false)
    } finally {
      setSubmitting(false)
    }
  }

  const isAuthor = currentUid && comment.firebase_uid === currentUid

  return (
    <div className="space-y-3">
      <div className="bg-gray-50/70 rounded-2xl border border-gray-100 p-4 space-y-2 hover:border-gray-200 transition">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white font-bold text-[10px] flex items-center justify-center shrink-0 overflow-hidden shadow-2xs">
              {comment.author_avatar ? (
                <img src={comment.author_avatar} alt="" className="w-full h-full object-cover" />
              ) : (
                (comment.author_name || 'U').charAt(0).toUpperCase()
              )}
            </div>
            <button
              type="button"
              onClick={() => onUserClick({ firebase_uid: comment.firebase_uid, author_name: comment.author_name })}
              className="font-bold text-gray-800 hover:text-blue-600 transition"
            >
              {comment.author_name || 'Student'}
            </button>
          </div>
          <span className="text-gray-400 text-[11px]">{fmtDate(comment.created_at)}</span>
        </div>

        <p className="text-xs sm:text-sm text-gray-700 leading-relaxed whitespace-pre-wrap pl-8">
          {comment.content}
        </p>

        <div className="flex items-center justify-between pt-1.5 pl-8 text-xs text-gray-500 border-t border-gray-100">
          <button
            type="button"
            onClick={() => setShowReplyBox(!showReplyBox)}
            className="font-semibold text-blue-600 hover:text-blue-800 transition flex items-center gap-1 text-[11px]"
          >
            <span>↩</span> Reply
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onReport(comment.id)}
              className="text-gray-400 hover:text-red-500 transition text-[11px]"
            >
              🚩 Report
            </button>
            {(isAuthor || isAdmin) && (
              <button
                type="button"
                onClick={() => onDelete(comment.id)}
                className="text-gray-400 hover:text-red-600 transition text-[11px]"
              >
                🗑️ Delete
              </button>
            )}
          </div>
        </div>

        {/* Reply form */}
        {showReplyBox && (
          <form onSubmit={handleSendReply} className="pt-2 pl-8 space-y-2">
            <textarea
              rows={2}
              value={replyText}
              onChange={e => setReplyText(e.target.value)}
              placeholder={`Reply to ${comment.author_name}…`}
              className="w-full text-xs p-2.5 bg-white border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowReplyBox(false)}
                className="px-3 py-1 text-xs text-gray-500 hover:bg-gray-200 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !replyText.trim()}
                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg shadow-2xs disabled:opacity-50"
              >
                {submitting ? 'Sending…' : 'Send'}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Nested Replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div className="pl-6 sm:pl-8 space-y-2.5 border-l-2 border-blue-100">
          {comment.replies.map(reply => (
            <PaperCommentItem
              key={reply.id}
              comment={reply}
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

export default function PaperDetailPage() {
  const { id } = useParams()
  const { user, isAuthenticated, isAdmin } = useAuth()

  const [paper, setPaper] = useState(null)
  const [related, setRelated] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [downloadCount, setDownloadCount] = useState(0)

  // Likes state
  const [likesCount, setLikesCount] = useState(0)
  const [hasLiked, setHasLiked] = useState(false)
  const [liking, setLiking] = useState(false)

  // Comments state
  const [comments, setComments] = useState([])
  const [commentsLoading, setCommentsLoading] = useState(false)
  const [newCommentText, setNewCommentText] = useState('')
  const [submittingComment, setSubmittingComment] = useState(false)
  const [commentError, setCommentError] = useState(null)

  // Modals state
  const [reportCommentId, setReportCommentId] = useState(null)
  const [profileUser, setProfileUser] = useState(null)

  const showToast = useCallback((msg) => setToast(msg), [])

  const loadLikesAndComments = useCallback(async (paperId) => {
    try {
      const [likesRes, commentsRes] = await Promise.all([
        getPaperLikes(paperId).catch(() => ({ likes_count: 0, has_liked: false })),
        getPaperComments(paperId).catch(() => []),
      ])
      setLikesCount(likesRes.likes_count || 0)
      setHasLiked(likesRes.has_liked || false)
      setComments(commentsRes || [])
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    setError(null)
    const isNumeric = /^\d+$/.test(id)
    const fetchFn = isNumeric ? getPaper(id) : getPaperBySlug(id)

    fetchFn
      .then(res => {
        const p = res.data
        setPaper(p)
        setDownloadCount(p.download_count ?? 0)
        if (p?.title) {
          document.title = `${p.title} | TN Board Portal`
        }

        // Anonymous Analytics Tracking
        trackPaperView(p.id, p.subjects?.class_id, p.subject_id)

        // Load interactions
        loadLikesAndComments(p.id)

        if (p.subject_id) {
          getPapersForSubject(p.subject_id)
            .then(r => setRelated(r.data.filter(rp => rp.id !== p.id).slice(0, 4)))
            .catch(() => {})
        }
      })
      .catch(err => setError(err.message || 'Paper not found'))
      .finally(() => setLoading(false))
  }, [id, loadLikesAndComments])

  const handleLikeToggle = async () => {
    if (!paper || liking) return

    if (!isAuthenticated) {
      showToast('Signing in with Google to like this paper…')
      const { user: authedUser, error: authError } = await signInWithGoogle()
      if (authError || !authedUser) {
        showToast('Sign-in cancelled or failed.')
        return
      }
    }

    setLiking(true)
    try {
      const res = await togglePaperLike(paper.id)
      setHasLiked(res.has_liked)
      setLikesCount(res.likes_count)
    } catch (err) {
      showToast(err.message || 'Failed to toggle like.')
    } finally {
      setLiking(false)
    }
  }

  const handleDownload = useCallback(async () => {
    if (!paper) return

    try {
      await recordDownload(paper.id)
      trackDownload(paper.id)
      setDownloadCount(c => c + 1)
      downloadPaper(paper.public_url, paper.title, paper.original_filename)
    } catch (err) {
      showToast(err.message || 'Failed to record download')
    }
  }, [paper, showToast])

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

  const handlePostComment = async (parentId = null, text = newCommentText) => {
    if (!text.trim() || !paper) return

    if (!isAuthenticated) {
      showToast('Signing in with Google to post comment…')
      const { user: authedUser, error: authError } = await signInWithGoogle()
      if (authError || !authedUser) {
        showToast('Sign-in cancelled or failed.')
        return
      }
    }

    setSubmittingComment(true)
    setCommentError(null)
    try {
      await addPaperComment(paper.id, {
        content: text.trim(),
        parent_id: parentId,
        author_avatar: user?.photoURL || null,
      })
      setNewCommentText('')
      const refreshed = await getPaperComments(paper.id)
      setComments(refreshed || [])
      showToast('Comment posted successfully!')
    } catch (err) {
      setCommentError(err.message || 'Failed to post comment.')
    } finally {
      setSubmittingComment(false)
    }
  }

  const handleDeleteComment = async (commentId) => {
    if (!window.confirm('Are you sure you want to delete this comment?')) return
    try {
      await deletePaperComment(commentId)
      const refreshed = await getPaperComments(paper.id)
      setComments(refreshed || [])
      showToast('Comment deleted.')
    } catch (err) {
      showToast(err.message || 'Failed to delete comment.')
    }
  }

  if (loading) return <div className="max-w-4xl mx-auto px-4 py-12"><LoadingSpinner text="Loading paper…" /></div>
  if (error) return <div className="max-w-4xl mx-auto px-4 py-12"><ErrorMessage message={error} /></div>
  if (!paper) return null

  const isQuestion = paper.paper_type === 'question'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Toast */}
      {toast && <Toast message={toast} onDone={() => setToast(null)} />}

      {/* Modals */}
      {profileUser && (
        <UserProfileModal
          uid={profileUser.firebase_uid}
          authorName={profileUser.author_name}
          onClose={() => setProfileUser(null)}
        />
      )}

      {reportCommentId && (
        <ReportModal
          targetType="comment"
          targetId={reportCommentId}
          onClose={() => setReportCommentId(null)}
          onSuccess={() => showToast('Report submitted for moderation.')}
        />
      )}

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

      <div className="card p-6 sm:p-8 space-y-6">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center shrink-0 text-2xl">
            {isQuestion ? '📄' : '✅'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className={`badge text-xs ${isQuestion ? 'bg-blue-100 text-blue-700' : 'bg-emerald-100 text-emerald-700'}`}>
                {isQuestion ? 'Question Paper' : 'Answer Key'}
              </span>
              {paper.contributor_name && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200/70 rounded-full">
                  <span>🏆 Contributed by:</span>
                  <strong className="text-amber-900">{paper.contributor_name}</strong>
                </span>
              )}
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-gray-900 mt-2 leading-snug">{paper.title}</h1>
          </div>
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Class',     value: paper.subjects?.classes?.name || '—' },
            { label: 'Subject',   value: paper.subjects?.name || '—' },
            { label: 'Exam Type', value: paper.exam_type },
            { label: 'Year',      value: paper.month ? `${paper.month} ${paper.year}` : paper.year },
            paper.district ? { label: 'District', value: paper.district } : null,
          ].filter(Boolean).map(m => (
            <div key={m.label} className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{m.label}</p>
              <p className="text-sm font-semibold text-gray-800 mt-0.5">{m.value}</p>
            </div>
          ))}
        </div>

        {/* ── Action & Interaction Bar ── */}
        <div className="flex flex-wrap items-center gap-3 pt-2">
          {/* View PDF */}
          {paper.public_url && (
            <button
              onClick={() => viewPdf(paper.public_url, paper.title, paper.original_filename)}
              className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold px-6 py-3 rounded-xl transition-colors text-sm shadow-sm"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View Paper
            </button>
          )}

          {/* Download PDF */}
          {paper.public_url && (
            <button
              onClick={handleDownload}
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-800 font-semibold px-5 py-3 rounded-xl border border-gray-200 transition-colors text-sm shadow-2xs"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
              </svg>
              {isQuestion ? 'Download QP' : 'Download Key'}
            </button>
          )}

          {/* Like Button */}
          <button
            onClick={handleLikeToggle}
            disabled={liking}
            className={`inline-flex items-center justify-center gap-2 font-semibold px-4 py-3 rounded-xl border transition-colors text-sm ${
              hasLiked
                ? 'bg-blue-50 border-blue-300 text-blue-700 font-bold'
                : 'bg-white hover:bg-gray-50 border-gray-200 text-gray-700'
            }`}
            title={hasLiked ? 'Unlike this paper' : 'Like this paper'}
          >
            <span>{hasLiked ? '👍 Liked' : '👍 Like'}</span>
            <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded-full text-xs font-bold">
              {likesCount}
            </span>
          </button>

          {/* Share */}
          <button
            onClick={handleShare}
            className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-600 font-semibold px-4 py-3 rounded-xl border border-gray-200 transition-colors text-sm"
            title="Share this paper"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            <span>Share</span>
          </button>
        </div>

        {/* Download count */}
        {downloadCount > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
            </svg>
            <span>{downloadCount.toLocaleString()} download{downloadCount !== 1 ? 's' : ''}</span>
          </div>
        )}

        {/* YouTube embed */}
        {paper.youtube_url && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <h2 className="text-lg font-bold text-gray-800 mb-3 flex items-center gap-2">
              <span className="text-red-500">▶</span> Video Explanation
            </h2>
            <YoutubeEmbed url={paper.youtube_url} />
          </div>
        )}
      </div>

      {/* ── Paper Comments & Questions Section ── */}
      <div className="card p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>💬</span> Questions &amp; Discussions ({comments.length})
          </h2>
        </div>

        {/* Add Comment Input */}
        {isAuthenticated ? (
          <form onSubmit={e => { e.preventDefault(); handlePostComment() }} className="space-y-3">
            {/* Authenticated Identity Context */}
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-2xl border border-gray-100">
              {user?.photoURL ? (
                <img src={user.photoURL} alt={user?.displayName || 'User'} className="w-8 h-8 rounded-full object-cover border border-gray-200" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white font-bold flex items-center justify-center text-xs">
                  {(user?.displayName || user?.email || 'U')[0].toUpperCase()}
                </div>
              )}
              <div className="text-xs">
                <span className="font-semibold text-gray-800">{user?.displayName || user?.email?.split('@')[0] || 'Student'}</span>
                <span className="text-gray-400 mx-1.5">·</span>
                <span className="text-gray-500">{user?.email}</span>
              </div>
            </div>

            {commentError && (
              <div className="p-3 bg-red-50 text-red-600 rounded-xl text-xs font-medium border border-red-200">
                {commentError}
              </div>
            )}
            <textarea
              rows={3}
              placeholder="Ask a question about this paper, share key insights, or discuss solutions…"
              value={newCommentText}
              onChange={e => setNewCommentText(e.target.value)}
              maxLength={2000}
              className="w-full text-sm border border-gray-200 rounded-2xl p-3.5 outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              required
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={submittingComment || !newCommentText.trim()}
                className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl transition flex items-center gap-2 shadow-xs"
              >
                {submittingComment ? <span className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '💬 Post Comment'}
              </button>
            </div>
          </form>
        ) : (
          <div className="p-6 bg-gray-50 rounded-2xl border border-gray-200 text-center space-y-2.5">
            <p className="text-xs text-gray-600 font-medium">
              Sign in with Google to post questions or answer other students.
            </p>
            <button
              onClick={signInWithGoogle}
              className="px-5 py-2.5 bg-white border border-gray-200 hover:bg-gray-100 text-gray-800 text-xs font-semibold rounded-xl transition shadow-2xs inline-flex items-center gap-2"
            >
              <span>🔐</span> Sign in with Google to Discuss
            </button>
          </div>
        )}

        {/* Threaded comments list */}
        {comments.length === 0 ? (
          <div className="p-8 text-center text-xs text-gray-400 bg-gray-50/50 rounded-2xl border border-dashed border-gray-200">
            No questions or comments yet on this paper. Start the discussion above!
          </div>
        ) : (
          <div className="space-y-3.5">
            {comments.map(c => (
              <PaperCommentItem
                key={c.id}
                comment={c}
                onReply={(parentId, text) => handlePostComment(parentId, text)}
                onDelete={handleDeleteComment}
                onReport={cid => setReportCommentId(cid)}
                onUserClick={u => setProfileUser(u)}
                currentUid={user?.uid}
                isAdmin={isAdmin}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Related Papers ── */}
      {related.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
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
      <div>
        <Link to={`/subject/${paper.subject_id}`} className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
          ← Back to {paper.subjects?.name || 'Subject'}
        </Link>
      </div>
    </div>
  )
}
