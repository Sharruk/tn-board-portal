import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { createSubmission } from '../services/submissions'
import UserAvatar from '../components/common/UserAvatar'


const ALLOWED_TYPES = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
const MAX_FILE_SIZE_MB = 25
const MAX_FILES = 5

function getExt(filename) {
  return filename.split('.').pop().toLowerCase()
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const FILE_ICONS = {
  pdf:  { icon: '📄', color: 'bg-red-50 text-red-600 border-red-200' },
  doc:  { icon: '📝', color: 'bg-blue-50 text-blue-600 border-blue-200' },
  docx: { icon: '📝', color: 'bg-blue-50 text-blue-600 border-blue-200' },
  jpg:  { icon: '🖼️', color: 'bg-purple-50 text-purple-600 border-purple-200' },
  jpeg: { icon: '🖼️', color: 'bg-purple-50 text-purple-600 border-purple-200' },
  png:  { icon: '🖼️', color: 'bg-purple-50 text-purple-600 border-purple-200' },
}

function FileTag({ file, onRemove }) {
  const ext = getExt(file.name)
  const meta = FILE_ICONS[ext] || { icon: '📎', color: 'bg-gray-50 text-gray-600 border-gray-200' }
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm ${meta.color}`}>
      <span>{meta.icon}</span>
      <span className="font-medium truncate max-w-[160px]">{file.name}</span>
      <span className="text-xs opacity-70">({formatSize(file.size)})</span>
      <button
        type="button"
        onClick={() => onRemove(file)}
        className="ml-1 opacity-60 hover:opacity-100 transition-opacity shrink-0"
        aria-label={`Remove ${file.name}`}
      >
        ✕
      </button>
    </div>
  )
}

import { useAuth } from '../contexts/AuthContext'
import { signInWithGoogle } from '../lib/firebase'

export default function SubmitMaterialPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const [form, setForm] = useState({
    publisher_name: user?.displayName || user?.email?.split('@')[0] || '',
    details: '',
  })

  // Sync publisher_name when user loads
  useEffect(() => {
    if (user && !form.publisher_name) {
      setForm(f => ({ ...f, publisher_name: user.displayName || user.email?.split('@')[0] || '' }))
    }
  }, [user])

  const [files, setFiles] = useState([])
  const [fileError, setFileError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const handleChange = e =>
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleFileChange = e => {
    setFileError(null)
    const incoming = Array.from(e.target.files || [])
    const combined = [...files, ...incoming]

    // Validate total count
    if (combined.length > MAX_FILES) {
      setFileError(`You can attach up to ${MAX_FILES} files per submission.`)
      e.target.value = ''
      return
    }

    // Validate each new file
    for (const file of incoming) {
      const ext = getExt(file.name)
      if (!ALLOWED_TYPES.includes(ext)) {
        setFileError(
          `"${file.name}" has an unsupported type (.${ext}). Allowed: ${ALLOWED_TYPES.join(', ')}.`
        )
        e.target.value = ''
        return
      }
      if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        setFileError(
          `"${file.name}" is too large (${formatSize(file.size)}). Max size is ${MAX_FILE_SIZE_MB} MB.`
        )
        e.target.value = ''
        return
      }
    }

    setFiles(combined)
    e.target.value = ''
  }

  const removeFile = fileToRemove => {
    setFiles(prev => prev.filter(f => f !== fileToRemove))
    setFileError(null)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setError(null)

    if (files.length === 0) {
      setFileError('Please attach at least one file.')
      return
    }

    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('publisher_name', form.publisher_name.trim())
      if (form.details.trim()) {
        formData.append('details', form.details.trim())
      }
      files.forEach(f => formData.append('files', f))

      await createSubmission(formData)
      setSuccess(true)
    } catch (err) {
      setError(err.message || 'Submission failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (authLoading) {
    return <div className="min-h-screen flex justify-center items-center">Loading...</div>
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-4 py-16">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-5 text-2xl">
            🔒
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-3">Sign in Required</h2>
          <p className="text-gray-600 text-base leading-relaxed mb-6">
            You must be signed in to submit educational material. This helps us ensure the quality and authenticity of contributions.
          </p>
          <button
            onClick={signInWithGoogle}
            className="inline-flex items-center justify-center gap-3 bg-white hover:bg-gray-50 border border-gray-200 text-gray-800 font-semibold px-6 py-3 rounded-xl transition-colors text-sm shadow-sm"
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

  if (success) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center px-4 py-16">
        <div className="max-w-lg w-full bg-white border border-gray-200/90 rounded-3xl p-8 sm:p-10 shadow-lg text-center space-y-6 animate-fade-in">
          <div className="w-20 h-20 bg-emerald-100/90 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto shadow-inner text-4xl">
            ✅
          </div>
          
          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-extrabold text-gray-900">
              Submission Received!
            </h2>
            <p className="text-sm font-semibold text-emerald-700">
              Thank you for contributing to the TN Board community.
            </p>
          </div>

          <p className="text-gray-600 text-xs sm:text-sm leading-relaxed bg-gray-50/90 p-4 rounded-2xl border border-gray-100">
            Your educational material has been submitted successfully and is currently <strong>under review</strong>. Once verified, it will be published with your contributor name. You can track its live status from <strong>My Contributions</strong>.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Link
              to="/my-contributions"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl transition shadow-xs"
            >
              <span>📂</span> View My Contributions
            </Link>
            <Link
              to="/"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 font-bold text-xs rounded-xl transition"
            >
              <span>🏠</span> Back to Home
            </Link>
          </div>

          <div className="pt-3 border-t border-gray-100">
            <button
              onClick={() => {
                setSuccess(false)
                setForm({ publisher_name: user?.displayName || user?.email?.split('@')[0] || '', details: '' })
                setFiles([])
              }}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 transition inline-flex items-center gap-1"
            >
              <span>➕</span> Submit Another Material
            </button>
          </div>
        </div>
      </div>
    )
  }


  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50/60 to-gray-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">

        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-5 shadow-lg shadow-blue-200">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 mb-2">Submit Your Material</h1>
          <p className="text-gray-500 text-base max-w-md mx-auto">
            Share question papers, answer keys, study notes, or other educational resources
            with students across Tamil Nadu.
          </p>
        </div>

        {/* Review notice */}
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-5 py-4 mb-8">
          <span className="text-amber-500 text-xl shrink-0 mt-0.5">⚡</span>
          <div>
            <p className="text-amber-800 font-semibold text-sm">Review Required</p>
            <p className="text-amber-700 text-sm mt-0.5">
              Your submission will be reviewed before it is published. This ensures
              quality and accuracy for all students.
            </p>
          </div>
        </div>

        {/* Form */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
          <form onSubmit={handleSubmit} className="space-y-6" noValidate>

            {/* Authenticated User Identity Card */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50/40 border border-blue-100 rounded-2xl p-4 sm:p-5 flex items-center justify-between">
              <div className="flex items-center gap-3.5">
                <UserAvatar
                  user={user}
                  name={user?.displayName}
                  size="lg"
                  className="border-2 border-white shadow-xs"
                />
                <div>
                  <div className="text-xs font-semibold text-blue-700 uppercase tracking-wider">Authenticated Contributor</div>
                  <div className="text-base font-bold text-gray-900">{user?.displayName || user?.email?.split('@')[0] || 'Contributor'}</div>
                  <div className="text-xs text-gray-500 font-medium">{user?.email}</div>
                </div>
              </div>
              <span className="hidden sm:inline-flex items-center gap-1 text-xs px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 font-semibold">
                ✓ Google Account
              </span>
            </div>

            {/* Publisher / Contributor Name */}
            <div>
              <label
                htmlFor="publisher_name"
                className="block text-sm font-semibold text-gray-700 mb-1.5"
              >
                Publisher / Contributor Name <span className="text-red-500">*</span>
              </label>
              <input
                id="publisher_name"
                name="publisher_name"
                type="text"
                value={form.publisher_name}
                onChange={handleChange}
                required
                autoFocus
                placeholder="e.g. Rajesh Kumar, Chennai"
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-800 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition placeholder-gray-400"
              />
            </div>



            {/* Files */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1.5">
                Material Files <span className="text-red-500">*</span>
              </label>
              <p className="text-xs text-gray-400 mb-2">
                PDF, Word (DOC/DOCX), or images (JPG/PNG) · Max {MAX_FILES} files · Max {MAX_FILE_SIZE_MB} MB each
              </p>

              {/* File drop zone */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full border-2 border-dashed border-gray-200 hover:border-blue-400 rounded-xl py-8 px-4 text-center transition-colors group"
              >
                <div className="text-3xl mb-2">📎</div>
                <p className="text-sm font-medium text-gray-600 group-hover:text-blue-600 transition-colors">
                  Click to choose files
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {ALLOWED_TYPES.join(', ')} · up to {MAX_FILES} files
                </p>
              </button>

              <input
                ref={fileInputRef}
                id="files"
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                className="hidden"
              />

              {/* File list */}
              {files.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {files.map((f, i) => (
                    <FileTag key={`${f.name}-${i}`} file={f} onRemove={removeFile} />
                  ))}
                </div>
              )}

              {/* File count indicator */}
              {files.length > 0 && (
                <p className="text-xs text-gray-400 mt-2">
                  {files.length} / {MAX_FILES} file{files.length !== 1 ? 's' : ''} selected
                </p>
              )}

              {/* File error */}
              {fileError && (
                <div className="mt-2 flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-3 py-2.5">
                  <svg className="w-4 h-4 text-red-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm text-red-600">{fileError}</p>
                </div>
              )}
            </div>

            {/* Additional Details */}
            <div>
              <label
                htmlFor="details"
                className="block text-sm font-semibold text-gray-700 mb-1.5"
              >
                Additional Details
                <span className="ml-1.5 text-xs font-normal text-gray-400">(optional)</span>
              </label>
              <textarea
                id="details"
                name="details"
                value={form.details}
                onChange={handleChange}
                rows={4}
                placeholder="Describe the material: class, subject, exam type, year, district, or any other context that would help the reviewer..."
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-800 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition placeholder-gray-400 resize-none"
              />
            </div>

            {/* Global error */}
            {error && (
              <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <svg className="w-4 h-4 text-red-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              id="submit-material-btn"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-3.5 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Submitting…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                  </svg>
                  Submit Material
                </>
              )}
            </button>

          </form>
        </div>

        {/* Footer note */}
        <p className="text-center text-xs text-gray-400 mt-6">
          By submitting, you confirm this material is for educational use and does not
          violate any copyright. The admin team will review your submission.
        </p>

      </div>
    </div>
  )
}
