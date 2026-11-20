import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import StudyMaterialCard from '../components/StudyMaterialCard'
import ReportModal from '../components/ReportModal'
import UserProfileModal from '../components/UserProfileModal'
import UserAvatar from '../components/common/UserAvatar'
import {
  getStudyMaterialBySlug,
  downloadMaterialFile,
  getMaterialsBySubject,
  getClassGeneralMaterials,
  toggleMaterialLike,
  getMaterialLikes,
  getMaterialComments,
  addMaterialComment,
  deleteMaterialComment,
} from '../services/studyMaterials'
import { downloadFile, viewPdf } from '../utils/download'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

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

function getYouTubeEmbedUrl(url) {
  if (!url) return null
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/
  const match = url.match(regExp)
  return (match && match[2].length === 11) ? `https://www.youtube-nocookie.com/embed/${match[2]}` : null
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
function StudyMaterialCommentItem({ comment, onReply, onDelete, onReport, onUserClick, currentUid, isAdmin }) {
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
            <UserAvatar
              src={comment.author_avatar}
              name={comment.author_name}
              size="xs"
            />
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
            <StudyMaterialCommentItem
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

export default function StudyMaterialDetailPage() {
  const { slug } = useParams()
  const { user, isAuthenticated, isAdmin } = useAuth()

  const [material, setMaterial] = useState(null)
  const [related, setRelated] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [downloadingFileId, setDownloadingFileId] = useState(null)

  // Likes state
  const [likesCount, setLikesCount] = useState(0)
  const [hasLiked, setHasLiked] = useState(false)
  const [liking, setLiking] = useState(false)

  // Comments state
  const [comments, setComments] = useState([])
  const [newCommentText, setNewCommentText] = useState('')
  const [submittingComment, setSubmittingComment] = useState(false)
  const [commentError, setCommentError] = useState(null)

  // Modals state
  const [reportCommentId, setReportCommentId] = useState(null)
  const [profileUser, setProfileUser] = useState(null)

  const showToast = useCallback((msg) => setToast(msg), [])

  const loadLikesAndComments = useCallback(async (materialId) => {
    try {
      const [likesRes, commentsRes] = await Promise.all([
        getMaterialLikes(materialId).catch(() => ({ likes_count: 0, has_liked: false })),
        getMaterialComments(materialId).catch(() => []),
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
    getStudyMaterialBySlug(slug)
      .then(res => {
        setMaterial(res)
        if (res?.title) {
          document.title = `${res.title} | TN Board Portal`
        }

        // Load interactions
        loadLikesAndComments(res.id)

        // Load related study materials
        if (res.subject_id) {
          getMaterialsBySubject(res.subject_id, { limit: 5 })
            .then(r => setRelated((r.data || []).filter(m => m.id !== res.id).slice(0, 4)))
            .catch(() => {})
        } else if (res.class_id) {
          getClassGeneralMaterials(res.class_id, { limit: 5 })
            .then(r => setRelated((r.data || []).filter(m => m.id !== res.id).slice(0, 4)))
            .catch(() => {})
        }
      })
      .catch(err => {
        setError(err.message || 'Study material not found')
      })
      .finally(() => setLoading(false))
  }, [slug, loadLikesAndComments])

  const handleLikeToggle = async () => {
    if (!material || liking) return

    if (!isAuthenticated) {
      showToast('Signing in with Google to like this material…')
      const { user: authedUser, error: authError } = await signInWithGoogle()
      if (authError || !authedUser) {
        showToast('Sign-in cancelled or failed.')
        return
      }
    }

    setLiking(true)
    try {
      const res = await toggleMaterialLike(material.id)
      setHasLiked(res.has_liked)
      setLikesCount(res.likes_count)
    } catch (err) {
      showToast(err.message || 'Failed to toggle like.')
    } finally {
      setLiking(false)
    }
  }

  const handleShare = useCallback(async () => {
    const url = window.location.href
    const shareData = {
      title: material?.title ?? 'TN Board Study Material',
      text: `Check out this TN State Board study material: ${material?.title}`,
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
  }, [material, showToast])

  const handlePostComment = async (parentId = null, text = newCommentText) => {
    if (!text.trim() || !material) return

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
      await addMaterialComment(material.id, {
        content: text.trim(),
        parent_id: parentId,
        author_avatar: user?.photoURL || null,
      })
      setNewCommentText('')
      const refreshed = await getMaterialComments(material.id)
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
      await deleteMaterialComment(commentId)
      const refreshed = await getMaterialComments(material.id)
      setComments(refreshed || [])
      showToast('Comment deleted.')
    } catch (err) {
      showToast(err.message || 'Failed to delete comment.')
    }
  }

  const handleDownload = async (file) => {
    try {
      setDownloadingFileId(file.id)
      const res = await downloadMaterialFile(material.id, file.id)
      const downloadUrl = res.download_url || file.public_url || file.file_url
      const filename = res.filename || file.display_filename || file.original_filename || `${material.title}.pdf`
      await downloadFile(downloadUrl, filename)

      // Optimistically increment download count
      setMaterial(prev => prev ? { ...prev, download_count: (prev.download_count || 0) + 1 } : null)
      showToast('Download started!')
    } catch (err) {
      console.error('Download error:', err)
      window.open(file.public_url || file.file_url, '_blank', 'noopener,noreferrer')
    } finally {
      setDownloadingFileId(null)
    }
  }

  const handlePreview = (file) => {
    const url = file.public_url || file.file_url
    if (!url) {
      showToast('No preview URL available for this file.')
      return
    }
    const isPdf = file.file_type === 'pdf' || 
                  file.mime_type === 'application/pdf' || 
                  (file.display_filename && file.display_filename.toLowerCase().endsWith('.pdf')) ||
                  (file.original_filename && file.original_filename.toLowerCase().endsWith('.pdf'))
    if (isPdf) {
      viewPdf(url, material.title, file.display_filename || file.original_filename || `${material.title}.pdf`)
    } else {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16">
        <LoadingSpinner text="Loading study material…" />
      </div>
    )
  }

  if (error || !material) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-12">
        <Breadcrumb items={[{ label: 'Home', href: '/' }, { label: 'Study Materials', href: '/study-materials' }, { label: 'Not Found' }]} />
        <div className="mt-6">
          <ErrorMessage message={error || 'Study material not found.'} />
          <div className="mt-4">
            <Link to="/study-materials" className="text-blue-600 hover:underline text-sm font-semibold">
              ← Back to Study Materials Hub
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const breadcrumbs = [
    { label: 'Home', href: '/' },
    { label: 'Study Materials', href: '/study-materials' },
  ]
  if (material.class_id) {
    breadcrumbs.push({
      label: material.class_name || `Class ${material.class_id}`,
      href: `/study-materials?class_id=${material.class_id}`,
    })
  }
  if (material.subject_name && material.subject_id) {
    breadcrumbs.push({
      label: material.subject_name,
      href: `/subject/${material.subject_id}`,
    })
  }
  if (material.category_name) {
    breadcrumbs.push({
      label: material.category_name,
      href: `/study-materials?category_id=${material.category_id}`,
    })
  }
  breadcrumbs.push({ label: material.title })

  const mediumLabel =
    material.medium === 'tamil' ? 'Tamil Medium (தமிழ் வழி)' :
    material.medium === 'english' ? 'English Medium' :
    material.medium === 'both' ? 'Both Mediums (Tamil & English)' : 'Universal'

  // Separate files into physical attachments vs external link resources
  const allFiles = material.files || []
  const physicalFiles = allFiles.filter(f => !f.external_url)
  const externalLinkFiles = allFiles.filter(f => Boolean(f.external_url))

  // Find primary file for top Action Controls (View / Download)
  const primaryFile = physicalFiles.find(f => {
    const isPdf = f.file_type === 'pdf' || f.mime_type === 'application/pdf' || f.display_filename?.toLowerCase().endsWith('.pdf')
    const isImg = f.file_type === 'image' || f.mime_type?.startsWith('image/')
    return isPdf || isImg
  }) || physicalFiles[0]

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
      <Breadcrumb items={breadcrumbs} />

      {/* ── Main Hero Detail Card ── */}
      <div className="card p-6 sm:p-8 space-y-6">
        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center shrink-0 text-2xl shadow-xs">
            📚
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="badge text-xs bg-blue-100 text-blue-700">
                Study Material
              </span>
              {material.category_name && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200/80">
                  <span>{material.category_name}</span>
                </span>
              )}
              {material.contributor_name && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200/70 rounded-full">
                  <span>🏆 Contributed by:</span>
                  <strong className="text-amber-900">{material.contributor_name}</strong>
                </span>
              )}
              {material.author_name && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 bg-amber-50 text-amber-800 border border-amber-200/70 rounded-full">
                  <span>✍️ Prepared by:</span>
                  <strong className="text-amber-900">{material.author_name}</strong>
                  {material.author_organization && (
                    <span className="text-amber-700 font-normal">({material.author_organization})</span>
                  )}
                </span>
              )}
            </div>

            <h1 className="text-xl sm:text-2xl font-extrabold text-gray-900 mt-2 leading-snug">
              {material.title}
            </h1>

            {/* Chapter / Unit / Term banner */}
            {(material.term || material.unit || material.chapter_name) && (
              <p className="text-sm font-semibold text-blue-600 mt-2">
                {[material.term, material.unit, material.chapter_name].filter(Boolean).join(' • ')}
              </p>
            )}

            {/* Description Box */}
            {material.description && (
              <p className="text-xs sm:text-sm text-gray-600 mt-3 leading-relaxed bg-gray-50/80 p-3 sm:p-4 rounded-xl border border-gray-100 whitespace-pre-line">
                {material.description}
              </p>
            )}
          </div>
        </div>

        {/* ── Metadata Grid Cards ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
          {[
            { label: 'Class',    value: material.class_name || (material.class_id ? `Class ${material.class_id}` : 'All Classes') },
            { label: 'Subject',  value: material.subject_name || 'General / Class-wide' },
            { label: 'Category', value: material.category_name || 'General Resource' },
            { label: 'Medium',   value: mediumLabel },
            material.academic_year ? { label: 'Year', value: material.academic_year } : null,
          ].filter(Boolean).map(m => (
            <div key={m.label} className="bg-gray-50 rounded-xl p-3">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">{m.label}</p>
              <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate" title={m.value}>{m.value}</p>
            </div>
          ))}
        </div>

        {/* ── Action & Interaction Bar ── */}
        <div className="flex flex-wrap items-center gap-3 pt-2">
          {/* Primary View / Preview Button */}
          {primaryFile && (
            <button
              onClick={() => handlePreview(primaryFile)}
              className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold px-6 py-3 rounded-xl transition-colors text-sm shadow-sm"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span>View Material</span>
            </button>
          )}

          {/* Primary Download Button */}
          {primaryFile && (
            <button
              onClick={() => handleDownload(primaryFile)}
              disabled={downloadingFileId === primaryFile.id}
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-50 text-gray-800 font-semibold px-5 py-3 rounded-xl border border-gray-200 transition-colors text-sm shadow-2xs disabled:opacity-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" />
              </svg>
              <span>{downloadingFileId === primaryFile.id ? 'Downloading…' : 'Download Material'}</span>
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
            title={hasLiked ? 'Unlike this material' : 'Like this material'}
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
            title="Share this material"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            <span>Share</span>
          </button>
        </div>

        {/* Telemetry info row */}
        <div className="pt-4 border-t border-gray-100 flex flex-wrap items-center justify-between gap-4 text-xs text-gray-500">
          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span>👁️</span> {material.view_count || 0} views
            </span>
            <span className="flex items-center gap-1.5">
              <span>⬇️</span> {material.download_count || 0} downloads
            </span>
          </div>

          <span className="text-gray-400">
            Updated {new Date(material.updated_at || material.created_at).toLocaleDateString('en-IN', {
              day: 'numeric',
              month: 'short',
              year: 'numeric',
            })}
          </span>
        </div>

        {/* Question formats & tags */}
        {(material.question_formats?.length > 0 || material.tags?.length > 0) && (
          <div className="pt-3 border-t border-gray-100 flex flex-wrap items-center gap-2">
            {material.question_formats?.map((qf, i) => (
              <span key={i} className="text-[11px] font-semibold bg-indigo-50 text-indigo-700 px-2.5 py-0.5 rounded-md border border-indigo-100">
                ✓ {qf.replace('_', ' ').toUpperCase()}
              </span>
            ))}
            {material.tags?.map((tag, i) => (
              <span key={i} className="text-[11px] font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded-md">
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* ── Download Attachments Section (multi-file materials only) ── */}
      {physicalFiles.length > 1 && (
        <div className="card p-6 sm:p-8 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <span>📥</span> Download Attachments ({physicalFiles.length})
            </h2>
          </div>

          <div className="space-y-3">
            {physicalFiles.map((file) => {
              const isPdf = file.file_type === 'pdf' || 
                            file.mime_type === 'application/pdf' || 
                            (file.display_filename && file.display_filename.toLowerCase().endsWith('.pdf')) ||
                            (file.original_filename && file.original_filename.toLowerCase().endsWith('.pdf'))
              const isImg = file.file_type === 'image' || file.mime_type?.startsWith('image/')
              const isDownloading = downloadingFileId === file.id

              return (
                <div
                  key={file.id}
                  className="bg-white rounded-2xl border border-gray-200 p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-blue-200 transition"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center text-xl shrink-0">
                      {isPdf ? '📄' : isImg ? '🖼️' : '📦'}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-gray-900 truncate">
                        {file.display_filename || file.original_filename || file.file_title}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {formatBytes(file.file_size || file.file_size_bytes)} • {isPdf ? 'PDF Document' : isImg ? 'Image' : (file.mime_type || 'Document')}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                    {(isPdf || isImg) && (
                      <button
                        type="button"
                        onClick={() => handlePreview(file)}
                        className="px-3.5 py-1.5 rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold transition flex items-center gap-1"
                      >
                        <span>👁️</span>
                        <span>Preview</span>
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={isDownloading}
                      onClick={() => handleDownload(file)}
                      className="px-4 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-xs"
                    >
                      {isDownloading ? (
                        <>
                          <span className="animate-spin text-xs">⏳</span>
                          <span>Downloading…</span>
                        </>
                      ) : (
                        <>
                          <span>⬇️</span>
                          <span>Download</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── External Learning Resources & YouTube Video ── */}
      {externalLinkFiles.length > 0 && (
        <div className="card p-6 sm:p-8 space-y-4">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <span>🔗</span> External Learning Resources ({externalLinkFiles.length})
          </h2>

          <div className="space-y-4">
            {externalLinkFiles.map((linkFile, idx) => {
              const url = linkFile.external_url
              const embedUrl = getYouTubeEmbedUrl(url)

              return (
                <div key={linkFile.id || idx} className="bg-gray-50/70 rounded-2xl border border-gray-200 p-5 shadow-xs">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        {embedUrl ? (
                          <span className="text-red-600 text-base">▶️</span>
                        ) : (
                          <span className="text-blue-600 text-base">🌐</span>
                        )}
                        <h3 className="text-sm font-bold text-gray-900">{linkFile.file_title || url}</h3>
                      </div>
                    </div>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3.5 py-1.5 rounded-xl bg-white border border-gray-200 hover:bg-blue-50 hover:text-blue-600 text-gray-700 text-xs font-semibold shrink-0 transition shadow-2xs"
                    >
                      Open Resource ↗
                    </a>
                  </div>

                  {embedUrl && (
                    <div className="mt-4 aspect-video rounded-xl overflow-hidden bg-black shadow-inner">
                      <iframe
                        src={embedUrl}
                        title={linkFile.file_title || 'Video explanation'}
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                        className="w-full h-full border-0"
                      />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ── Questions & Discussions (Comments) Section ── */}
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
              <UserAvatar user={user} size="sm" />
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
              placeholder="Ask a question about this study material, share key notes, or discuss problems…"
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
              Sign in with Google to post questions or discuss this study material.
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
            No questions or comments yet on this study material. Start the discussion above!
          </div>
        ) : (
          <div className="space-y-3.5">
            {comments.map(c => (
              <StudyMaterialCommentItem
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

      {/* ── Related Study Materials ── */}
      {related.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              More study materials from {material.subject_name || material.class_name || 'this class'}
            </h2>
            <Link
              to={material.subject_id ? `/subject/${material.subject_id}` : `/study-materials?class_id=${material.class_id}`}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              View all →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {related.map(m => (
              <StudyMaterialCard
                key={m.id}
                material={m}
                showSubject={!material.subject_id}
                showClass={!material.class_id}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── Bottom Navigation Links ── */}
      <div className="pt-6 border-t border-gray-200 flex items-center justify-between">
        <Link
          to={material.subject_id ? `/subject/${material.subject_id}` : '/study-materials'}
          className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1.5"
        >
          <span>←</span> Back to {material.subject_name || 'All Study Materials'}
        </Link>

        <Link
          to="/submit-material"
          className="text-xs font-semibold text-gray-500 hover:text-gray-700"
        >
          Have better notes? Submit material →
        </Link>
      </div>
    </div>
  )
}
