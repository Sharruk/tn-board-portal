import { useEffect, useState, useCallback } from 'react'
import {
  getSubmissions,
  getSubmission,
  approveSubmission,
  rejectSubmission,
  restoreSubmission,
  deleteSubmission,
  downloadSubmissionFile,
} from '../../services/submissions'
import { getClasses, getSubjectsForClass } from '../../services/classes'
import { EXAM_TYPES, MONTHS, TN_DISTRICTS } from '../../services/papers'
import { viewPdf } from '../../utils/download'

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 10 }, (_, i) => CURRENT_YEAR - i)

const DEFAULT_THANK_YOU_MESSAGE =
  "🎉 Your contribution is now public!\nThank you for contributing to the TN Board community. Your contribution may help another student prepare better. ❤️"

const REJECTION_PRESETS = [
  {
    id: 'duplicate',
    label: 'Duplicate Submission',
    text: 'This paper has already been published through another contributor. Thank you for taking the time to contribute to the TN Board community. ❤️',
  },
  {
    id: 'poor_quality',
    label: 'Unreadable / Poor Quality',
    text: 'The uploaded pages or images are blurry, cut off, or difficult to read. Please resubmit with clear, well-lit photos or a scanned PDF.',
  },
  {
    id: 'incomplete',
    label: 'Incomplete Pages / Missing Sections',
    text: 'The submission appears to be missing essential pages, questions, or answer keys. Please re-upload the full paper.',
  },
  {
    id: 'incorrect_content',
    label: 'Incorrect / Unverified Content',
    text: 'The content could not be verified against the official TN State Board syllabus or exam requirements.',
  },
  {
    id: 'out_of_scope',
    label: 'Not Relevant / Out of Scope',
    text: 'This material does not match the TN State Board curriculum (Classes 9–12) or does not meet our publishing guidelines.',
  },
]


// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function fmtDatetime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatSize(bytes) {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function StatusBadge({ status }) {
  const styles = {
    pending:  'bg-amber-50  text-amber-700  border-amber-200',
    approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    rejected: 'bg-red-50   text-red-600    border-red-200',
  }
  const icons = { pending: '⏳', approved: '✅', rejected: '❌' }
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${styles[status] || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
      <span>{icons[status] || '•'}</span>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function Toast({ message, type, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000)
    return () => clearTimeout(t)
  }, [onDismiss])
  const colors = type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
  return (
    <div className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl ${colors} max-w-sm`}>
      <span className="text-lg">{type === 'success' ? '✅' : '❌'}</span>
      <p className="text-sm font-medium flex-1">{message}</p>
      <button onClick={onDismiss} className="ml-2 opacity-70 hover:opacity-100 text-lg leading-none">×</button>
    </div>
  )
}

// ── File type helpers ──────────────────────────────────────────────────────────

const IMAGE_TYPES = new Set(['jpg', 'jpeg', 'png'])
const PDF_TYPES   = new Set(['pdf'])
const DOC_TYPES   = new Set(['doc', 'docx'])

function fileIcon(type) {
  if (IMAGE_TYPES.has(type)) return '🖼️'
  if (PDF_TYPES.has(type))   return '📄'
  if (DOC_TYPES.has(type))   return '📝'
  return '📎'
}

function canPreview(type) {
  return IMAGE_TYPES.has(type) || PDF_TYPES.has(type)
}

// ── File Preview Modal ────────────────────────────────────────────────────────

function FilePreviewModal({ file, onClose }) {
  const [loadError, setLoadError] = useState(false)
  const [pdfLoaded, setPdfLoaded] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [dlError, setDlError] = useState(null)
  const type = file.file_type?.toLowerCase() || ''
  const url  = file.signed_url

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleDownload = async () => {
    setDlError(null)
    setDownloading(true)
    try {
      await downloadSubmissionFile(file.id, file.original_filename)
    } catch (err) {
      setDlError(err.message || 'Download failed. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl flex flex-col w-full max-w-4xl max-h-[92vh] overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-xl">{fileIcon(type)}</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">{file.original_filename}</p>
              <p className="text-xs text-gray-400">{type.toUpperCase()} · {formatSize(file.file_size)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-4">
            {dlError && (
              <p className="text-xs text-red-600 max-w-[180px] truncate">{dlError}</p>
            )}
            <button
              id={`download-file-modal-${file.id}`}
              onClick={handleDownload}
              disabled={downloading}
              className="text-xs font-semibold text-blue-600 border border-blue-200 bg-blue-50 hover:bg-blue-100 disabled:opacity-60 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
            >
              {downloading
                ? <span className="w-3 h-3 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
                : '⬇'}
              Download
            </button>
            <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 transition text-lg leading-none" aria-label="Close preview">✕</button>
          </div>
        </div>
        <div className="flex-1 overflow-auto flex items-center justify-center bg-gray-50 min-h-0 relative">
          {!url && (
            <div className="text-center p-10">
              <p className="text-4xl mb-3">🔒</p>
              <p className="text-sm font-semibold text-gray-700 mb-1">Preview unavailable</p>
              <p className="text-xs text-gray-400">No signed URL was generated for this file. Try refreshing the submission detail.</p>
            </div>
          )}
          {url && IMAGE_TYPES.has(type) && (
            <div className="p-4 flex items-center justify-center w-full h-full">
              {loadError ? (
                <div className="text-center">
                  <p className="text-4xl mb-3">⚠️</p>
                  <p className="text-sm font-semibold text-gray-700 mb-1">Unable to load image</p>
                  <p className="text-xs text-gray-400 mb-4">The signed URL may have expired, or the file could not be retrieved.</p>
                  <a href={url} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-blue-600 border border-blue-200 bg-blue-50 hover:bg-blue-100 px-4 py-2 rounded-lg transition-colors">
                    Try opening in new tab
                  </a>
                </div>
              ) : (
                <img src={url} alt={file.original_filename} className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-md" onError={() => setLoadError(true)} />
              )}
            </div>
          )}
          {url && PDF_TYPES.has(type) && (
            <div className="w-full h-full flex flex-col min-h-[60vh]">
              {loadError ? (
                <div className="flex-1 flex items-center justify-center p-10 text-center">
                  <div>
                    <p className="text-4xl mb-3">⚠️</p>
                    <p className="text-sm font-semibold text-gray-700 mb-1">Unable to embed PDF</p>
                    <p className="text-xs text-gray-400 mb-4">Your browser could not display this PDF inline.</p>
                    <button
                      onClick={() => viewPdf(url, file.original_filename, file.original_filename)}
                      className="text-xs font-semibold text-blue-600 border border-blue-200 bg-blue-50 hover:bg-blue-100 px-4 py-2 rounded-lg transition-colors"
                    >
                      Open PDF in new tab ↗
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {!pdfLoaded && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
                    </div>
                  )}
                  <iframe src={url} title={file.original_filename} className="w-full flex-1 min-h-[60vh] border-0" onLoad={() => setPdfLoaded(true)} onError={() => setLoadError(true)} />
                  <div className="px-4 py-2 bg-white border-t border-gray-100 shrink-0">
                    <button
                      onClick={() => viewPdf(url, file.original_filename, file.original_filename)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Open in new tab ↗
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
          {url && DOC_TYPES.has(type) && (
            <div className="text-center p-10">
              <p className="text-5xl mb-4">📝</p>
              <p className="text-sm font-semibold text-gray-800 mb-1">
                Preview unavailable for {type.toUpperCase()} files
              </p>
              <p className="text-xs text-gray-400 mb-6">
                Word documents cannot be previewed directly in the browser.<br />
                Download the file to inspect it in Microsoft Word or a compatible viewer.
              </p>
            </div>
          )}
          {url && !IMAGE_TYPES.has(type) && !PDF_TYPES.has(type) && !DOC_TYPES.has(type) && (
            <div className="text-center p-10">
              <p className="text-4xl mb-3">📎</p>
              <p className="text-sm font-semibold text-gray-700 mb-1">Preview unavailable for this file type</p>
              <p className="text-xs text-gray-400 mb-4">
                <strong>{type.toUpperCase()}</strong> files cannot be previewed in the browser.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── File Card ──────────────────────────────────────────────────────────────────

function SubmissionFileCard({ file }) {
  const [previewing, setPreviewing] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [dlError, setDlError] = useState(null)
  const type = file.file_type?.toLowerCase() || ''
  const url  = file.signed_url

  const handleDownload = async () => {
    setDlError(null)
    setDownloading(true)
    try {
      await downloadSubmissionFile(file.id, file.original_filename)
    } catch (err) {
      setDlError(err.message || 'Download failed. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <>
      <div className="flex items-center justify-between gap-3 bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xl shrink-0" aria-hidden="true">{fileIcon(type)}</span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">{file.original_filename}</p>
            <p className="text-xs text-gray-400">{type.toUpperCase()} · {formatSize(file.file_size)}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <div className="flex items-center gap-2">
            {url && canPreview(type) && (
              <button id={`preview-file-${file.id}`} onClick={() => setPreviewing(true)} className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors">
                👁 Preview
              </button>
            )}
            {url && DOC_TYPES.has(type) && (
              <button id={`view-file-${file.id}`} onClick={() => setPreviewing(true)} className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 border border-indigo-200 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors">
                📝 View
              </button>
            )}
            <button
              id={`download-file-${file.id}`}
              onClick={handleDownload}
              disabled={downloading}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 bg-blue-50 hover:bg-blue-100 disabled:opacity-60 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
            >
              {downloading
                ? <span className="w-3 h-3 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin" />
                : '⬇'}
              Download
            </button>
          </div>
          {dlError && (
            <p className="text-xs text-red-500">{dlError}</p>
          )}
        </div>
      </div>
      {previewing && <FilePreviewModal file={file} onClose={() => setPreviewing(false)} />}
    </>
  )
}

// ── Submission Detail Modal ────────────────────────────────────────────────────

function extractYouTubeId(url) {
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

function SubmissionDetailModal({ submission, classes, onClose, onReviewed, onRequestDelete }) {
  const initialFileName = submission.files?.[0]?.original_filename || ''
  const [approveForm, setApproveForm] = useState({
    title: '',
    downloadFilename: initialFileName,
    description: submission.details || '',
    youtubeUrl: '',
    classId: '',
    subjectId: '',
    examType: '',
    year: String(CURRENT_YEAR),
    paperType: 'question',
    month: '',
    district: '',
  })
  const [publishSource, setPublishSource]     = useState('original') // 'original' | 'prepared'
  const [preparedFile, setPreparedFile]       = useState(null)
  const [thankYouMessage, setThankYouMessage] = useState(DEFAULT_THANK_YOU_MESSAGE)
  const [titleManuallyEdited, setTitleManuallyEdited] = useState(false)
  const [filenameManuallyEdited, setFilenameManuallyEdited] = useState(Boolean(initialFileName))
  const [subjects, setSubjects]               = useState([])
  const [rejectReason, setRejectReason]       = useState('')
  const [selectedPresetId, setSelectedPresetId] = useState(null)
  const [showRejectForm, setShowRejectForm]   = useState(false)
  const [showRejectConfirm, setShowRejectConfirm] = useState(false)
  const [loading, setLoading]                 = useState(false)
  const [error, setError]                     = useState(null)

  useEffect(() => {
    if (!approveForm.classId) { setSubjects([]); return }
    getSubjectsForClass(approveForm.classId).then(r => setSubjects(r.data || []))
  }, [approveForm.classId])

  // Automatically construct clean default title and download filename when metadata changes
  useEffect(() => {
    const cls = classes.find(c => String(c.id) === String(approveForm.classId))?.name || ''
    const sub = subjects.find(s => String(s.id) === String(approveForm.subjectId))?.name || ''
    const typeStr = approveForm.paperType === 'question' ? 'Question Paper' : 'Answer Key'
    const parts = [
      cls,
      sub,
      approveForm.examType,
      approveForm.month,
      approveForm.year,
      approveForm.district,
      typeStr,
    ].filter(Boolean)
    if (parts.length >= 2) {
      const genTitle = parts.join(' ')
      if (!titleManuallyEdited) {
        setApproveForm(f => ({ ...f, title: genTitle }))
      }
      if (!filenameManuallyEdited && !initialFileName) {
        const typeCode = approveForm.paperType === 'question' ? 'QP' : 'Key'
        const fnParts = [
          cls.replace(/\s+/g, ''),
          sub.replace(/\s+/g, ''),
          (approveForm.examType || '').replace(/\s+/g, ''),
          approveForm.month || '',
          approveForm.year || '',
          (approveForm.district || '').replace(/\s+/g, ''),
          typeCode,
        ].filter(Boolean)
        setApproveForm(f => ({ ...f, downloadFilename: `${fnParts.join('_')}.pdf` }))
      }
    }
  }, [approveForm.classId, approveForm.subjectId, approveForm.examType, approveForm.month, approveForm.year, approveForm.district, approveForm.paperType, classes, subjects, titleManuallyEdited, filenameManuallyEdited, initialFileName])

  const ytId = extractYouTubeId(approveForm.youtubeUrl)

  const handleApprove = async () => {
    if (loading) return
    setError(null)
    if (!approveForm.classId)   return setError('Please select a class.')
    if (!approveForm.subjectId) return setError('Please select a subject.')
    if (!approveForm.examType)  return setError('Please select an exam type.')
    if (!approveForm.year)      return setError('Please select a year.')
    if (!approveForm.title.trim()) return setError('Please enter a paper title.')
    if (!approveForm.downloadFilename.trim()) return setError('Please enter a download file name.')
    if (approveForm.youtubeUrl.trim() && !extractYouTubeId(approveForm.youtubeUrl.trim())) {
      return setError('Please enter a valid YouTube video URL (e.g. https://youtube.com/watch?v=... or https://youtu.be/...) or leave it blank.')
    }
    if (publishSource === 'prepared' && !preparedFile) {
      return setError('Please select the prepared publication PDF file to upload.')
    }

    setLoading(true)
    try {
      if (publishSource === 'prepared' && preparedFile) {
        const formData = new FormData()
        formData.append('title', approveForm.title.trim())
        formData.append('download_filename', approveForm.downloadFilename.trim())
        if (approveForm.description.trim()) formData.append('description', approveForm.description.trim())
        if (thankYouMessage.trim()) formData.append('thank_you_message', thankYouMessage.trim())
        if (approveForm.youtubeUrl.trim()) formData.append('youtube_url', approveForm.youtubeUrl.trim())
        formData.append('class_id', String(approveForm.classId))
        formData.append('subject_id', String(approveForm.subjectId))
        formData.append('exam_type', approveForm.examType)
        formData.append('year', String(approveForm.year))
        formData.append('paper_type', approveForm.paperType)
        if (approveForm.month) formData.append('month', approveForm.month)
        if (approveForm.district) formData.append('district', approveForm.district)
        formData.append('prepared_file', preparedFile)

        await approveSubmission(submission.id, formData)
      } else {
        await approveSubmission(submission.id, {
          title:              approveForm.title.trim(),
          download_filename:  approveForm.downloadFilename.trim(),
          description:        approveForm.description.trim() || null,
          thank_you_message:  thankYouMessage.trim() || null,
          youtube_url:        approveForm.youtubeUrl.trim() || null,
          class_id:           parseInt(approveForm.classId, 10),
          subject_id:         parseInt(approveForm.subjectId, 10),
          exam_type:          approveForm.examType,
          year:               parseInt(approveForm.year, 10),
          paper_type:         approveForm.paperType,
          month:              approveForm.month || null,
          district:           approveForm.district || null,
        })
      }
      onReviewed('approved', submission.id)
      onClose()
    } catch (err) {
      setError(err.message || 'Approval failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Called after the user confirms the rejection dialog
  const handleReject = async () => {
    if (loading) return
    setError(null)
    setLoading(true)
    try {
      await rejectSubmission(submission.id, {
        rejection_reason: rejectReason.trim() || null,
      })
      onReviewed('rejected', submission.id)
      onClose()
    } catch (err) {
      setError(err.message || 'Rejection failed.')
    } finally {
      setLoading(false)
    }
  }

  const handleRestore = async () => {
    setError(null)
    setLoading(true)
    try {
      await restoreSubmission(submission.id)
      onReviewed('restored', submission.id)
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to restore submission.')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectPreset = (preset) => {
    setSelectedPresetId(preset.id)
    setRejectReason(preset.text)
  }

  const isPending  = submission.status === 'pending'
  const isRejected = submission.status === 'rejected'
  const isApproved = submission.status === 'approved'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between px-6 py-5 border-b border-gray-100">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Submission Detail</h2>
            <p className="text-xs text-gray-400 font-mono mt-0.5">{submission.id}</p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={submission.status} />
            <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 transition">✕</button>
          </div>
        </div>
        <div className="px-6 py-5 space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Contributor</p>
              <p className="text-sm font-semibold text-gray-800">{submission.publisher_name}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Email</p>
              <p className="text-sm text-gray-800">{submission.email}</p>
            </div>
          </div>
          {submission.details && (
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Submitter Notes</p>
              <p className="text-sm text-gray-700 whitespace-pre-wrap">{submission.details}</p>
            </div>
          )}
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span>Submitted: {fmtDatetime(submission.created_at)}</span>
            {submission.reviewed_at && (
              <span>Reviewed: {fmtDatetime(submission.reviewed_at)}</span>
            )}
          </div>
          {submission.status === 'rejected' && submission.rejection_reason && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4">
              <p className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-1">Rejection Reason</p>
              <p className="text-sm text-red-700">{submission.rejection_reason}</p>
            </div>
          )}
          {submission.status === 'approved' && submission.thank_you_message && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
              <p className="text-xs font-semibold text-emerald-800 uppercase tracking-wide mb-1">Thank-You Message</p>
              <p className="text-sm text-emerald-900 whitespace-pre-line">{submission.thank_you_message}</p>
            </div>
          )}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Original Files ({submission.files?.length || 0})
            </p>
            {!submission.files?.length ? (
              <p className="text-sm text-gray-400">No files attached.</p>
            ) : (
              <div className="space-y-2">
                {submission.files.map(file => (
                  <SubmissionFileCard key={file.id} file={file} />
                ))}
              </div>
            )}
          </div>

          {/* ── APPROVED: View Published Paper & Delete ────────────────── */}
          {isApproved && (
            <div className="border border-emerald-200 bg-emerald-50 rounded-2xl p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-emerald-900 flex items-center gap-2">
                    <span>✅</span> Approved &amp; Published
                  </p>
                  <p className="text-xs text-emerald-700 mt-1">
                    This submission has been approved and published to the public materials catalog. Contributor attribution remains preserved.
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <a
                    href="/admin/papers"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-semibold text-emerald-800 bg-white border border-emerald-300 hover:bg-emerald-100 px-4 py-2.5 rounded-xl transition-colors shrink-0 flex items-center justify-center gap-1.5 shadow-2xs"
                  >
                    <span>📄</span> View Published Paper ↗
                  </a>
                  <button
                    id="delete-approved-submission-btn"
                    onClick={() => onRequestDelete(submission)}
                    disabled={loading}
                    className="text-xs font-semibold text-red-600 hover:text-red-800 hover:bg-red-50 border border-red-200 bg-white py-2.5 px-4 rounded-xl transition-colors flex items-center gap-1.5 shadow-2xs"
                  >
                    <span>🗑️</span> Delete Submission
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── REJECTED: Restore to Pending & Delete ──────────────────── */}
          {isRejected && (
            <div className="border border-amber-200 bg-amber-50 rounded-2xl p-5 space-y-4">
              <div>
                <p className="text-sm font-bold text-amber-800 mb-1 flex items-center gap-2">
                  <span>↩</span> Rejected Submission Actions
                </p>
                <p className="text-xs text-amber-700">
                  This submission was rejected. You can move it back to <strong>Pending</strong> to review it again, or permanently delete it.
                </p>
              </div>
              {error && (
                <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
              )}
              <div className="flex flex-wrap items-center gap-2.5 pt-1">
                <button
                  id="restore-submission-btn"
                  onClick={handleRestore}
                  disabled={loading}
                  className="bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white text-sm font-semibold py-2.5 px-5 rounded-xl transition-colors flex items-center gap-2 shadow-2xs"
                >
                  {loading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '↩'}
                  Restore to Pending
                </button>
                <button
                  id="delete-submission-btn"
                  onClick={() => onRequestDelete(submission)}
                  disabled={loading}
                  className="text-xs font-semibold text-red-600 hover:text-red-800 hover:bg-red-50 border border-red-200 bg-white py-2.5 px-4 rounded-xl transition-colors flex items-center gap-1.5"
                >
                  <span>🗑️</span> Delete
                </button>
              </div>
            </div>
          )}

          {/* ── PENDING: Approve form & Delete ──────────────────────────── */}
          {isPending && !showRejectForm && !showRejectConfirm && (
            <div className="border border-emerald-200 bg-emerald-50/70 rounded-2xl p-5 sm:p-6 space-y-5">
              <div className="flex items-center justify-between border-b border-emerald-100 pb-3">
                <p className="text-base font-bold text-emerald-900 flex items-center gap-2">
                  <span>✅</span> Approve &amp; Publish Paper
                </p>
                <span className="text-xs font-semibold px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full">
                  Admin Action
                </span>
              </div>

              {/* ── Publication Choice: Original Files vs Admin Prepared PDF ── */}
              <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-2xs space-y-3">
                <p className="text-xs font-bold text-gray-800 uppercase tracking-wider">Publication File Choice</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <label
                    className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                      publishSource === 'original'
                        ? 'bg-emerald-50/60 border-emerald-400 ring-1 ring-emerald-400'
                        : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="publishSource"
                      value="original"
                      checked={publishSource === 'original'}
                      onChange={() => setPublishSource('original')}
                      className="mt-0.5 text-emerald-600 focus:ring-emerald-500"
                    />
                    <div className="text-xs">
                      <p className="font-bold text-gray-900">Use original uploaded file(s)</p>
                      <p className="text-gray-500 mt-0.5">Publish directly using the contributor's uploaded document.</p>
                    </div>
                  </label>
                  <label
                    className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                      publishSource === 'prepared'
                        ? 'bg-emerald-50/60 border-emerald-400 ring-1 ring-emerald-400'
                        : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="publishSource"
                      value="prepared"
                      checked={publishSource === 'prepared'}
                      onChange={() => setPublishSource('prepared')}
                      className="mt-0.5 text-emerald-600 focus:ring-emerald-500"
                    />
                    <div className="text-xs">
                      <p className="font-bold text-gray-900">Use prepared publication file (PDF)</p>
                      <p className="text-gray-500 mt-0.5">Upload a prepared/cleaned PDF. Contributor attribution is fully preserved.</p>
                    </div>
                  </label>
                </div>

                {publishSource === 'prepared' && (
                  <div className="mt-3 p-3.5 bg-blue-50/80 border border-blue-200 rounded-xl space-y-2">
                    <label className="block text-xs font-bold text-blue-900">
                      Upload Prepared PDF <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="file"
                      accept=".pdf,application/pdf"
                      onChange={e => {
                        const f = e.target.files?.[0] || null
                        setPreparedFile(f)
                      }}
                      className="block w-full text-xs text-gray-700 file:mr-3 file:py-2 file:px-3.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
                    />
                    <p className="text-[11px] text-blue-700">
                      💡 Original submission files will remain safely archived. The published catalog entry will credit <strong>{submission.publisher_name}</strong>.
                    </p>
                  </div>
                )}
              </div>

              {/* ── 1. Paper Title (Admin Editable) ── */}
              <div>
                <label className="block text-xs font-bold text-gray-800 mb-1">
                  Paper Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={approveForm.title}
                  onChange={e => {
                    setTitleManuallyEdited(true)
                    setApproveForm(f => ({ ...f, title: e.target.value }))
                  }}
                  placeholder="e.g. Class 10 Science Monthly Test Question Paper August 2026 - Chennai District"
                  className="w-full text-sm border border-gray-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none bg-white font-medium text-gray-900 placeholder:text-gray-400 shadow-2xs"
                  maxLength={255}
                  required
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  The public paper will be published with this human-readable title.
                </p>
              </div>

              {/* ── 2. Download File Name (Admin Editable) ── */}
              <div>
                <label className="block text-xs font-bold text-gray-800 mb-1">
                  Download File Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={approveForm.downloadFilename}
                  onChange={e => {
                    setFilenameManuallyEdited(true)
                    setApproveForm(f => ({ ...f, downloadFilename: e.target.value }))
                  }}
                  placeholder="e.g. Class10_Science_MonthlyTest_August2026_Chennai_QP.pdf"
                  className="w-full text-sm border border-gray-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none bg-white font-mono text-gray-900 placeholder:text-gray-400 shadow-2xs"
                  maxLength={255}
                  required
                />
                <p className="text-[11px] text-gray-500 mt-1">
                  This is the clean filename students receive when clicking Download (browser download).
                </p>
              </div>

              {/* ── 3. Description (Admin Editable) ── */}
              <div>
                <label className="block text-xs font-bold text-gray-800 mb-1 flex items-center justify-between">
                  <span>Description <span className="text-gray-400 font-normal">(optional)</span></span>
                  <span className="text-[11px] text-gray-400 font-normal">Shown on public paper detail page</span>
                </label>
                <textarea
                  rows={3}
                  value={approveForm.description}
                  onChange={e => setApproveForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Official Class 10 Science Monthly Test Question Paper for Chennai District conducted in August 2026. Download the question paper PDF and watch the explanation video for additional guidance."
                  className="w-full text-sm border border-gray-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none bg-white text-gray-900 placeholder:text-gray-400 shadow-2xs resize-none"
                  maxLength={2000}
                />
              </div>

              {/* ── 4. Approval Thank-You Message (Admin Editable) ── */}
              <div>
                <label className="block text-xs font-bold text-gray-800 mb-1 flex items-center justify-between">
                  <span>Approval Thank-You Message <span className="text-gray-400 font-normal">(shown to contributor)</span></span>
                  <button
                    type="button"
                    onClick={() => setThankYouMessage(DEFAULT_THANK_YOU_MESSAGE)}
                    className="text-[11px] text-emerald-700 hover:underline font-semibold"
                  >
                    Reset to Default
                  </button>
                </label>
                <textarea
                  rows={3}
                  value={thankYouMessage}
                  onChange={e => setThankYouMessage(e.target.value)}
                  placeholder="Thank-you note displayed to the contributor upon approval…"
                  className="w-full text-sm border border-gray-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none bg-white text-gray-900 placeholder:text-gray-400 shadow-2xs resize-none"
                  maxLength={2000}
                />
              </div>

              {/* ── 5. YouTube Explanation Video URL (Optional) ── */}
              <div>
                <label className="block text-xs font-bold text-gray-800 mb-1 flex items-center justify-between">
                  <span>YouTube Explanation Video <span className="text-gray-400 font-normal">(optional)</span></span>
                  <span className="text-[11px] text-gray-400 font-normal">Embeds video on paper page</span>
                </label>
                <input
                  type="url"
                  value={approveForm.youtubeUrl}
                  onChange={e => setApproveForm(f => ({ ...f, youtubeUrl: e.target.value }))}
                  placeholder="https://youtube.com/watch?v=... or https://youtu.be/..."
                  className="w-full text-sm border border-gray-200 rounded-xl px-3.5 py-2.5 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none bg-white font-medium text-gray-900 placeholder:text-gray-400 shadow-2xs"
                />
                {ytId && (
                  <div className="mt-2.5 rounded-xl overflow-hidden border border-gray-200 bg-white shadow-2xs">
                    <img
                      src={`https://img.youtube.com/vi/${ytId}/mqdefault.jpg`}
                      alt="YouTube thumbnail preview"
                      className="w-full h-32 object-cover"
                      onError={e => { e.currentTarget.style.display = 'none' }}
                    />
                    <p className="px-3 py-1.5 text-xs text-gray-600 bg-gray-50 font-medium">▶ Video preview ready for published paper</p>
                  </div>
                )}
              </div>

              {/* ── Paper Academic Metadata ── */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Class <span className="text-red-500">*</span></label>
                  <select
                    value={approveForm.classId}
                    onChange={e => setApproveForm(f => ({ ...f, classId: e.target.value, subjectId: '' }))}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none bg-white font-medium"
                  >
                    <option value="">Select class…</option>
                    {classes.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Subject <span className="text-red-500">*</span></label>
                  <select
                    value={approveForm.subjectId}
                    onChange={e => setApproveForm(f => ({ ...f, subjectId: e.target.value }))}
                    disabled={!approveForm.classId}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none disabled:opacity-50 bg-white font-medium"
                  >
                    <option value="">Select subject…</option>
                    {subjects.map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Exam Type <span className="text-red-500">*</span></label>
                  <select
                    value={approveForm.examType}
                    onChange={e => setApproveForm(f => ({ ...f, examType: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none bg-white font-medium"
                  >
                    <option value="">Select exam type…</option>
                    {EXAM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Year <span className="text-red-500">*</span></label>
                  <select
                    value={approveForm.year}
                    onChange={e => setApproveForm(f => ({ ...f, year: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none bg-white font-medium"
                  >
                    {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Paper Type <span className="text-red-500">*</span></label>
                  <select
                    value={approveForm.paperType}
                    onChange={e => setApproveForm(f => ({ ...f, paperType: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none bg-white font-medium"
                  >
                    <option value="question">Question Paper</option>
                    <option value="answer_key">Answer Key</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Month <span className="text-gray-400 font-normal">(optional)</span></label>
                  <select
                    value={approveForm.month}
                    onChange={e => setApproveForm(f => ({ ...f, month: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none bg-white font-medium"
                  >
                    <option value="">Select month…</option>
                    {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-bold text-gray-700 mb-1">District <span className="text-gray-400 font-normal">(optional)</span></label>
                  <select
                    value={approveForm.district}
                    onChange={e => setApproveForm(f => ({ ...f, district: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-emerald-500 outline-none bg-white font-medium"
                  >
                    <option value="">No specific district (State-wide)</option>
                    {TN_DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
              </div>

              {error && (
                <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2">
                  <span className="shrink-0 mt-0.5">⚠️</span>
                  <span>{error}</span>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-between gap-2.5 pt-2 border-t border-emerald-100/80">
                <div className="flex gap-2 flex-1 min-w-[240px]">
                  <button
                    id="approve-submission-btn"
                    onClick={handleApprove}
                    disabled={loading}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 text-white text-sm font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm shadow-emerald-200"
                  >
                    {loading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '✅'}
                    Approve &amp; Publish
                  </button>
                  <button
                    onClick={() => { setShowRejectForm(true); setError(null) }}
                    disabled={loading}
                    className="px-4 py-3 border border-red-200 text-red-600 hover:bg-red-50 text-sm font-semibold rounded-xl transition-colors"
                  >
                    Reject
                  </button>
                </div>
                <button
                  id="delete-submission-btn"
                  onClick={() => onRequestDelete(submission)}
                  disabled={loading}
                  className="px-3 py-2.5 text-xs font-semibold text-red-600 hover:text-red-800 hover:bg-red-50 border border-red-200 bg-white rounded-xl transition-colors flex items-center gap-1.5"
                >
                  <span>🗑️</span> Delete
                </button>
              </div>
            </div>
          )}

          {/* ── PENDING: Rejection reason form ──────────────────────────── */}
          {isPending && showRejectForm && !showRejectConfirm && (
            <div className="border border-red-200 bg-red-50 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-bold text-red-800 flex items-center gap-2">
                  <span>❌</span> Select or Enter Rejection Reason
                </p>
                <span className="text-[11px] font-semibold text-red-600 bg-red-100 px-2 py-0.5 rounded-md">
                  5 Presets + Custom
                </span>
              </div>

              {/* ── Preset Buttons ── */}
              <div>
                <p className="text-xs font-bold text-gray-700 mb-2">Preset Reasons:</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {REJECTION_PRESETS.map(preset => {
                    const active = selectedPresetId === preset.id
                    return (
                      <button
                        key={preset.id}
                        type="button"
                        onClick={() => handleSelectPreset(preset)}
                        className={`text-left text-xs p-2.5 rounded-xl border transition-all ${
                          active
                            ? 'bg-red-600 text-white border-red-600 font-semibold shadow-2xs'
                            : 'bg-white text-gray-800 border-red-200 hover:bg-red-100/60 font-medium'
                        }`}
                      >
                        <p className="font-bold">{preset.label}</p>
                        <p className={`text-[11px] line-clamp-2 mt-0.5 ${active ? 'text-red-100' : 'text-gray-500'}`}>
                          {preset.text}
                        </p>
                      </button>
                    )
                  })}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-gray-700">
                    Reason Message <span className="text-gray-400 font-normal">(editable, visible in rejection history)</span>
                  </label>
                  {rejectReason && (
                    <button
                      type="button"
                      onClick={() => { setRejectReason(''); setSelectedPresetId(null) }}
                      className="text-[11px] text-gray-500 hover:text-red-600 underline"
                    >
                      Clear message
                    </button>
                  )}
                </div>
                <textarea
                  value={rejectReason}
                  onChange={e => {
                    setRejectReason(e.target.value)
                    setSelectedPresetId(null)
                  }}
                  rows={3}
                  placeholder="Select a preset above or write a custom reason…"
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-red-500 outline-none resize-none bg-white text-gray-900 shadow-2xs"
                  maxLength={1000}
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => { setShowRejectConfirm(true); setError(null) }}
                  disabled={loading}
                  className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 rounded-xl transition-colors"
                >
                  Continue →
                </button>
                <button
                  onClick={() => { setShowRejectForm(false); setError(null) }}
                  className="px-4 py-2.5 border border-gray-200 text-gray-600 hover:bg-gray-50 text-sm font-semibold rounded-xl transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* ── PENDING: Rejection confirmation ─────────────────────────── */}
          {isPending && showRejectConfirm && (
            <div className="border border-red-300 bg-red-50 rounded-2xl p-5">
              <p className="text-sm font-bold text-red-800 mb-2 flex items-center gap-2"><span>⚠️</span> Confirm Rejection</p>
              <p className="text-sm text-red-700 mb-1">
                Are you sure you want to reject this submission?
              </p>
              <p className="text-xs text-red-600 mb-4">
                It will be moved to <strong>Rejected</strong>. You can restore it back to Pending later if needed.
              </p>
              {rejectReason && (
                <div className="bg-red-100 border border-red-200 rounded-lg px-3 py-2 mb-4">
                  <p className="text-xs font-semibold text-red-700 mb-0.5">Reason recorded:</p>
                  <p className="text-xs text-red-700 italic">"{rejectReason}"</p>
                </div>
              )}
              {error && (
                <p className="text-xs text-red-600 mb-3 bg-red-100 border border-red-200 rounded-lg px-3 py-2">{error}</p>
              )}
              <div className="flex gap-2">
                <button
                  id="reject-submission-btn"
                  onClick={handleReject}
                  disabled={loading}
                  className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  {loading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '❌'}
                  Yes, Reject Submission
                </button>
                <button
                  onClick={() => { setShowRejectConfirm(false); setError(null) }}
                  disabled={loading}
                  className="px-4 py-2.5 border border-gray-200 text-gray-600 hover:bg-gray-50 text-sm font-semibold rounded-xl transition-colors"
                >
                  Go Back
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


// ── Delete Confirmation Modal ──────────────────────────────────────────────────

function DeleteConfirmModal({ submission, onClose, onDeleted }) {
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const handleDelete = async () => {
    if (loading) return
    setError(null)
    setLoading(true)
    try {
      await deleteSubmission(submission.id)
      onDeleted(submission.id)
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to delete submission. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-xs" onClick={() => !loading && onClose()} aria-hidden="true" />
      <div className="relative z-10 bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4 border border-red-100">
        <div className="flex items-center gap-3 text-red-600">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-xl shrink-0">
            ⚠️
          </div>
          <div>
            <h3 className="text-base font-bold text-gray-900">Delete this submission permanently?</h3>
            <p className="text-xs text-gray-500 font-mono mt-0.5">ID: {submission.id}</p>
          </div>
        </div>

        {submission.status === 'approved' ? (
          <div className="space-y-2 text-xs text-red-700 bg-red-50 border border-red-200 rounded-xl p-3.5">
            <p className="font-bold text-sm text-red-800">This submission has already been approved and published.</p>
            <p className="text-gray-700 font-medium">Deleting it will permanently remove:</p>
            <ul className="list-disc list-inside space-y-1 text-gray-700 font-medium pl-1">
              <li>The submission record and submission files</li>
              <li>Private uploaded files from storage</li>
              <li>The associated published paper in the library</li>
              <li>Associated public PDF files from CDN storage</li>
              <li>Related discussions, comments, and likes</li>
            </ul>
            <p className="text-red-600 font-semibold pt-1">This action cannot be undone.</p>
          </div>
        ) : (
          <p className="text-sm text-gray-600 leading-relaxed">
            This will permanently remove the submission and its uploaded files from storage. This action cannot be undone.
          </p>
        )}

        <div className="bg-gray-50 border border-gray-200 rounded-xl p-3.5 space-y-1.5 text-xs text-gray-600">
          <div className="flex justify-between">
            <span className="font-semibold text-gray-500">Contributor:</span>
            <span className="font-medium text-gray-800 truncate max-w-[200px]">{submission.publisher_name}</span>
          </div>
          <div className="flex justify-between">
            <span className="font-semibold text-gray-500">Email:</span>
            <span className="font-medium text-gray-800 truncate max-w-[200px]">{submission.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="font-semibold text-gray-500">Status:</span>
            <span className="font-bold uppercase tracking-wider">{submission.status}</span>
          </div>
          <div className="flex justify-between">
            <span className="font-semibold text-gray-500">Submitted:</span>
            <span>{fmtDate(submission.created_at)}</span>
          </div>
        </div>

        {error && (
          <div className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2">
            <span className="shrink-0 mt-0.5">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        <div className="flex gap-2.5 pt-2">
          <button
            id="cancel-delete-submission-btn"
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-2.5 border border-gray-200 text-gray-700 hover:bg-gray-50 text-sm font-semibold rounded-xl transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            id="confirm-delete-submission-btn"
            onClick={handleDelete}
            disabled={loading}
            className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-semibold py-2.5 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 shadow-sm shadow-red-200"
          >
            {loading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : '🗑️'}
            Delete Permanently
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SubmissionsPage() {
  const [submissions, setSubmissions]               = useState([])
  const [loading, setLoading]                       = useState(true)
  const [error, setError]                           = useState(null)
  const [statusFilter, setStatusFilter]             = useState('pending')
  const [selected, setSelected]                     = useState(null)
  const [deletingSubmission, setDeletingSubmission] = useState(null)
  const [classes, setClasses]                       = useState([])
  const [toast, setToast]                           = useState(null)

  useEffect(() => {
    getClasses().then(r => setClasses(r.data || []))
  }, [])

  const loadSubmissions = useCallback(async (filter) => {
    setLoading(true)
    setError(null)
    try {
      const res = await getSubmissions(filter || null)
      setSubmissions(res.data || [])
    } catch (err) {
      setError(err.message || 'Failed to load submissions.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSubmissions(statusFilter)
  }, [statusFilter, loadSubmissions])

  const openDetail = async (sub) => {
    try {
      const detail = await getSubmission(sub.id)
      setSelected(detail)
    } catch (err) {
      setToast({ type: 'error', message: err.message || 'Failed to load submission detail.' })
    }
  }

  const handleReviewed = (action, id) => {
    const labels = {
      approved: 'approved and published',
      rejected: 'rejected',
      restored: 'moved back to Pending',
      deleted:  'deleted',
    }
    const label = labels[action] || action
    setToast({ type: 'success', message: `Submission ${label} successfully.` })
    loadSubmissions(statusFilter)
  }

  const handleDeleted = (id) => {
    if (selected && selected.id === id) {
      setSelected(null)
    }
    setDeletingSubmission(null)
    setToast({ type: 'success', message: 'Submission deleted successfully.' })
    loadSubmissions(statusFilter)
  }

  const pendingCount = submissions.filter(s => s.status === 'pending').length

  return (
    <div className="p-6 md:p-8 max-w-6xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">Material Submissions</h1>
          <p className="text-gray-500 text-sm mt-1">Review and approve publicly submitted educational materials.</p>
        </div>
        {pendingCount > 0 && (
          <div className="hidden sm:flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-700 text-sm font-semibold px-4 py-2 rounded-xl">
            <span>⏳</span>
            {pendingCount} pending review{pendingCount !== 1 ? 's' : ''}
          </div>
        )}
      </div>
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit mb-6">
        {['pending', 'approved', 'rejected', null].map(s => {
          const label = s ? (s.charAt(0).toUpperCase() + s.slice(1)) : 'All'
          const active = statusFilter === s
          return (
            <button
              key={String(s)}
              onClick={() => setStatusFilter(s)}
              className={`px-4 py-1.5 text-sm font-semibold rounded-lg transition-all ${
                active ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              {label}
            </button>
          )
        })}
      </div>
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-6 text-sm text-red-600">
          {error}
        </div>
      )}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        ) : submissions.length === 0 ? (
          <div className="text-center py-20 px-6">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-500 font-medium">
              No {statusFilter || ''} submissions found.
            </p>
            {statusFilter === 'pending' && (
              <p className="text-gray-400 text-sm mt-1">
                Submissions from the public form will appear here.
              </p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['Contributor', 'Email', 'Files', 'Submitted', 'Status', 'Actions'].map(h => (
                    <th key={h} className="px-5 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {submissions.map(sub => (
                  <tr key={sub.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-5 py-3">
                      <p className="font-semibold text-gray-800 truncate max-w-[160px]">{sub.publisher_name}</p>
                      {sub.details && (
                        <p className="text-xs text-gray-400 truncate max-w-[160px] mt-0.5">{sub.details}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{sub.email}</td>
                    <td className="px-4 py-3 text-center">
                      <span className="inline-flex items-center justify-center w-7 h-7 bg-blue-50 text-blue-700 text-xs font-bold rounded-full border border-blue-100">
                        {sub.file_count || 0}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">{fmtDate(sub.created_at)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={sub.status} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <button
                          id={`view-submission-${sub.id}`}
                          onClick={() => openDetail(sub)}
                          className="text-xs font-semibold text-blue-600 hover:text-blue-800 border border-blue-200 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors"
                        >
                          {sub.status === 'pending' ? 'Review' : 'View'}
                        </button>
                        <button
                          id={`delete-submission-table-${sub.id}`}
                          onClick={() => setDeletingSubmission(sub)}
                          className="text-xs font-semibold text-red-600 hover:text-red-800 border border-red-200 bg-red-50 hover:bg-red-100 px-2.5 py-1.5 rounded-lg transition-colors"
                          title="Delete submission permanently"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {selected && (
        <SubmissionDetailModal
          submission={selected}
          classes={classes}
          onClose={() => setSelected(null)}
          onReviewed={handleReviewed}
          onRequestDelete={(sub) => setDeletingSubmission(sub)}
        />
      )}
      {deletingSubmission && (
        <DeleteConfirmModal
          submission={deletingSubmission}
          onClose={() => setDeletingSubmission(null)}
          onDeleted={handleDeleted}
        />
      )}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}
    </div>
  )
}

