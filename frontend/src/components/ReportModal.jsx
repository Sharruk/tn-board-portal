import { useState } from 'react'
import { submitReport } from '../services/community'

export default function ReportModal({ targetType, targetId, onClose, onSuccess }) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!reason.trim()) {
      setError('Please provide a reason for the report.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await submitReport({
        target_type: targetType,
        target_id: String(targetId),
        reason: reason.trim(),
      })
      if (onSuccess) onSuccess()
      onClose()
    } catch (err) {
      setError(err.message || 'Failed to submit report. Please sign in.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-gray-100 relative">
        <h3 className="text-lg font-bold text-gray-900 mb-1 flex items-center gap-2">
          <span>🚩</span> Report Content
        </h3>
        <p className="text-xs text-gray-500 mb-4">
          Please explain why this content violates community guidelines (e.g. spam, incorrect educational content, inappropriate language).
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-xl text-xs font-medium border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={4}
            className="w-full text-sm p-3 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition"
            placeholder="Describe the issue in detail…"
            required
          />

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 text-sm bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl shadow transition disabled:opacity-50"
            >
              {loading ? 'Submitting…' : 'Submit Report'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
