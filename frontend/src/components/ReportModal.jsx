import { useState } from 'react'
import { submitReport } from '../services/community'
import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'

const PAPER_CATEGORIES = [
  { value: 'incorrect_answer_key', label: '❌ Incorrect Answer Key' },
  { value: 'blurred_scan', label: '📄 Blurred / Illegible Scan' },
  { value: 'missing_pages', label: '📑 Missing Pages' },
  { value: 'wrong_subject_or_class', label: '🏷️ Wrong Subject or Class' },
  { value: 'wrong_exam_or_year', label: '📅 Wrong Exam or Year' },
  { value: 'duplicate_paper', label: '📋 Duplicate Paper' },
  { value: 'watermark_abuse', label: '💧 Heavy / Obtrusive Watermark' },
  { value: 'syllabus_mismatch', label: '📚 Outdated / Syllabus Mismatch' },
  { value: 'copyright_infringement', label: '©️ Copyright Violation' },
  { value: 'inappropriate_content', label: '⚠️ Inappropriate Content' },
  { value: 'other', label: '💬 Other Issue' },
]

const GENERAL_CATEGORIES = [
  { value: 'spam', label: '🚫 Spam or Advertising' },
  { value: 'harassment', label: '✋ Harassment or Abuse' },
  { value: 'inappropriate_content', label: '⚠️ Inappropriate Content' },
  { value: 'misinformation', label: '❓ Misinformation' },
  { value: 'other', label: '💬 Other' },
]

export default function ReportModal({ targetType, targetId, onClose, onSuccess }) {
  const { isAuthenticated } = useAuth()
  const isPaper = targetType === 'paper'
  const categories = isPaper ? PAPER_CATEGORIES : GENERAL_CATEGORIES

  const [category, setCategory] = useState(categories[0].value)
  const [reason, setReason] = useState('')
  const [details, setDetails] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!reason.trim()) {
      setError('Please provide a summary reason for the report.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await submitReport({
        target_type: targetType,
        target_id: String(targetId),
        reason: reason.trim(),
        report_category: category,
        details: details.trim() || undefined,
      })
      if (onSuccess) onSuccess()
      onClose()
    } catch (err) {
      if (err.status === 409 || err.message?.includes('409') || err.message?.includes('already pending')) {
        setError('You already have an active report pending review for this item.')
      } else {
        setError(err.message || 'Failed to submit report. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-gray-100 relative">
        <h3 className="text-lg font-bold text-gray-900 mb-1 flex items-center gap-2">
          <span>🚩</span> Report {isPaper ? 'Question Paper' : 'Content'}
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Reports are reviewed by teachers and administrators. Please help us maintain the highest educational quality.
        </p>

        {!isAuthenticated ? (
          <div className="text-center py-6 space-y-3">
            <p className="text-sm text-gray-600">
              You must be signed in to submit a report to prevent duplicate and malicious submissions.
            </p>
            <div className="flex justify-center gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  onClose()
                  signInWithGoogle()
                }}
                className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition shadow-xs"
              >
                <span>🔐</span> Sign in with Google
              </button>
            </div>
          </div>
        ) : (
          <>
            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-xl text-xs font-medium border border-red-200">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">
                  Category <span className="text-red-500">*</span>
                </label>
                <select
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  className="w-full text-xs p-2.5 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition"
                >
                  {categories.map(cat => (
                    <option key={cat.value} value={cat.value}>
                      {cat.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">
                  Reason <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={reason}
                  onChange={e => setReason(e.target.value)}
                  className="w-full text-xs p-2.5 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition"
                  placeholder="e.g. Q4 answer key specifies option B instead of C"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1.5">
                  Additional Details (Optional)
                </label>
                <textarea
                  value={details}
                  onChange={e => setDetails(e.target.value)}
                  rows={3}
                  className="w-full text-xs p-2.5 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition"
                  placeholder="Include question number, textbook page reference, or correction details…"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={loading}
                  className="px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-5 py-2 text-xs bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl shadow transition disabled:opacity-50"
                >
                  {loading ? 'Submitting…' : 'Submit Report'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
