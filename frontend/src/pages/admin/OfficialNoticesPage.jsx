import { useEffect, useState, useCallback } from 'react'
import { getAdminNotices, uploadNotice, updateNotice, deleteNotice } from '../../services/admin'
import { getClasses } from '../../services/classes'
import { NOTICE_CATEGORIES, CATEGORY_ICONS, isValidYouTubeUrl } from '../../services/notices'

// ── Constants ─────────────────────────────────────────────────────────────────

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 10 }, (_, i) => CURRENT_YEAR - i)
const CLASSES = [9, 10, 11, 12]

const ACCEPTED_EXTENSIONS = '.pdf,.jpg,.jpeg,.png,.gif,.webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx'

const EMPTY_FORM = {
  title: '', category: '', classId: '', year: String(CURRENT_YEAR),
  description: '', expiresAt: '', youtubeUrl: '', file: null,
}

// ── Shared sub-components (same patterns as PapersPage) ──────────────────────

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

function Modal({ title, onClose, children }) {
  useEffect(() => {
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth
    document.body.style.overflow = 'hidden'
    if (scrollbarWidth > 0) document.body.style.paddingRight = `${scrollbarWidth}px`
    return () => { document.body.style.overflow = ''; document.body.style.paddingRight = '' }
  }, [])

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg flex flex-col"
        style={{ maxHeight: '90vh' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors" aria-label="Close">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="overflow-y-auto overscroll-contain px-6 py-5 flex-1 min-h-0">
          {children}
        </div>
      </div>
    </div>
  )
}

function FormField({ label, required, children, hint, error }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-1.5">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-gray-400">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-500 font-medium">{error}</p>}
    </div>
  )
}

const inputCls    = 'w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-800 outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition bg-white'
const inputErrCls = 'w-full px-3 py-2.5 border border-red-300 rounded-xl text-sm text-gray-800 outline-none focus:ring-2 focus:ring-red-300 focus:border-red-400 transition bg-white'

// ── CategoryBadge ─────────────────────────────────────────────────────────────

function CategoryBadge({ category }) {
  const icon = CATEGORY_ICONS[category] ?? '📄'
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700">
      {icon} {category}
    </span>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export default function AdminOfficialNoticesPage() {
  const [notices, setNotices]   = useState([])
  const [classes, setClasses]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [toast, setToast]       = useState(null)

  // Modal states
  const [showUpload, setShowUpload] = useState(false)
  const [editNotice, setEditNotice] = useState(null)
  const [deleteId, setDeleteId]     = useState(null)

  // Upload form
  const [form, setForm]         = useState(EMPTY_FORM)
  const [formLoading, setFormLoading] = useState(false)
  const [formErrors, setFormErrors]   = useState({})
  const [uploadProgress, setUploadProgress] = useState(null)

  // Edit form
  const [editForm, setEditForm] = useState({
    title: '', category: '', classId: '', year: String(CURRENT_YEAR),
    description: '', expiresAt: '', youtubeUrl: '', isVisible: false, isPinned: false,
  })
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError]     = useState(null)

  // Filters
  const [filterCategory, setFilterCategory] = useState('')
  const [filterVisible, setFilterVisible]   = useState('')

  const showToast = (message, type = 'success') => setToast({ message, type })

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([getAdminNotices(), getClasses()])
      .then(([noticesRes, classesRes]) => {
        setNotices(noticesRes.data)
        setClasses(classesRes.data)
      })
      .catch(err => setError(err.message || 'Failed to load data'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = notices.filter(n => {
    if (filterCategory && n.category !== filterCategory) return false
    if (filterVisible === 'visible'  && !n.is_visible) return false
    if (filterVisible === 'hidden'   && n.is_visible)  return false
    if (filterVisible === 'pinned'   && !n.is_pinned)  return false
    return true
  })

  // ── Upload form handlers ────────────────────────────────────────────────────

  const handleFormChange = e => {
    const { name, value, files } = e.target
    if (name === 'file') {
      const f = files[0] || null
      setFormErrors(fe => ({ ...fe, file: null }))
      setForm(prev => ({ ...prev, file: f }))
    } else {
      setForm(f => ({ ...f, [name]: value }))
      if (formErrors[name]) setFormErrors(fe => ({ ...fe, [name]: null }))
    }
  }

  const validateForm = () => {
    const errors = {}
    if (!form.title.trim())   errors.title    = 'Title is required'
    if (!form.category)       errors.category = 'Please select a category'
    if (!form.file)           errors.file     = 'A file is required'
    if (form.youtubeUrl && !isValidYouTubeUrl(form.youtubeUrl))
      errors.youtubeUrl = 'Enter a valid YouTube URL (youtu.be, youtube.com/watch?v=, or youtube.com/shorts/)'
    return errors
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    const errors = validateForm()
    if (Object.keys(errors).length > 0) { setFormErrors(errors); return }
    setFormLoading(true)
    setFormErrors({})
    setUploadProgress(0)
    try {
      const fd = new FormData()
      fd.append('title',       form.title)
      fd.append('category',    form.category)
      if (form.classId) fd.append('class_id', form.classId)
      fd.append('year',        form.year)
      if (form.description) fd.append('description', form.description)
      if (form.expiresAt)   fd.append('expires_at', new Date(form.expiresAt).toISOString())
      if (form.youtubeUrl)  fd.append('youtube_url', form.youtubeUrl.trim())
      fd.append('file', form.file)
      await uploadNotice(fd, pct => setUploadProgress(pct))
      setShowUpload(false)
      setForm(EMPTY_FORM)
      setUploadProgress(null)
      load()
      showToast('Notice uploaded! Set it to Visible when ready.')
    } catch (err) {
      setFormErrors({ _general: err.message || 'Upload failed. Please try again.' })
      setUploadProgress(null)
    } finally {
      setFormLoading(false)
    }
  }

  // ── Edit handlers ───────────────────────────────────────────────────────────

  const openEdit = (n) => {
    setEditNotice(n)
    setEditForm({
      title:       n.title || '',
      category:    n.category || '',
      classId:     n.class_id ? String(n.class_id) : '',
      year:        String(n.year || CURRENT_YEAR),
      description: n.description || '',
      expiresAt:   n.expires_at ? n.expires_at.slice(0, 10) : '',
      youtubeUrl:  n.youtube_url || '',
      isVisible:   n.is_visible ?? false,
      isPinned:    n.is_pinned  ?? false,
    })
    setEditError(null)
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    // Validate YouTube URL before submitting
    if (editForm.youtubeUrl && !isValidYouTubeUrl(editForm.youtubeUrl)) {
      setEditError('Enter a valid YouTube URL (youtu.be, youtube.com/watch?v=, or youtube.com/shorts/)')
      return
    }
    setEditLoading(true)
    setEditError(null)
    try {
      const payload = {
        title:       editForm.title.trim(),
        category:    editForm.category,
        class_id:    editForm.classId ? parseInt(editForm.classId, 10) : null,
        year:        parseInt(editForm.year, 10),
        description: editForm.description || null,
        youtube_url: editForm.youtubeUrl.trim() || null,
        expires_at:  editForm.expiresAt ? new Date(editForm.expiresAt).toISOString() : null,
        is_visible:  editForm.isVisible,
        is_pinned:   editForm.isPinned,
      }
      await updateNotice(editNotice.id, payload)
      setEditNotice(null)
      load()
      showToast('Notice updated successfully!')
    } catch (err) {
      setEditError(err.message || 'Update failed')
    } finally {
      setEditLoading(false)
    }
  }

  // ── Delete handler ──────────────────────────────────────────────────────────

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteNotice(deleteId)
      setDeleteId(null)
      load()
      showToast('Notice deleted.')
    } catch (err) {
      showToast(err.message || 'Delete failed', 'error')
    }
  }

  // ── Quick-toggle visibility / pin ───────────────────────────────────────────

  const toggleVisible = async (n) => {
    try {
      await updateNotice(n.id, { is_visible: !n.is_visible })
      load()
      showToast(n.is_visible ? 'Notice hidden.' : 'Notice published!')
    } catch (err) {
      showToast(err.message || 'Failed', 'error')
    }
  }

  const togglePin = async (n) => {
    try {
      await updateNotice(n.id, { is_pinned: !n.is_pinned })
      load()
      showToast(n.is_pinned ? 'Notice unpinned.' : 'Notice pinned!')
    } catch (err) {
      showToast(err.message || 'Failed', 'error')
    }
  }

  // ==========================================================================
  // Render
  // ==========================================================================

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">Official Notices</h1>
          <p className="text-gray-500 text-sm mt-1">
            {notices.length} notice{notices.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={() => { setShowUpload(true); setFormErrors({}); setForm(EMPTY_FORM) }}
          className="btn-primary"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload Notice
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          className="text-sm border border-gray-200 rounded-xl px-3 py-2 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-100"
        >
          <option value="">All Categories</option>
          {NOTICE_CATEGORIES.map(c => (
            <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>
          ))}
        </select>
        <select
          value={filterVisible}
          onChange={e => setFilterVisible(e.target.value)}
          className="text-sm border border-gray-200 rounded-xl px-3 py-2 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-100"
        >
          <option value="">All Status</option>
          <option value="visible">Visible</option>
          <option value="hidden">Hidden</option>
          <option value="pinned">Pinned</option>
        </select>
        {(filterCategory || filterVisible) && (
          <button
            onClick={() => { setFilterCategory(''); setFilterVisible('') }}
            className="text-sm text-red-500 hover:text-red-700 font-medium px-2"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <span className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
          </div>
        ) : error ? (
          <p className="text-center py-16 text-red-500">{error}</p>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 px-6">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-500 font-medium">
              {notices.length === 0 ? 'No notices uploaded yet.' : 'No notices match the current filters.'}
            </p>
            {notices.length === 0 && (
              <button onClick={() => setShowUpload(true)} className="mt-4 btn-primary">
                Upload First Notice
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['#', 'Title', 'Category', 'Class', 'Year', 'File', 'Views', 'Downloads', 'Expires', 'Status', 'Actions'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map(n => {
                  const isExpired = n.expires_at && new Date(n.expires_at) < new Date()
                  return (
                    <tr key={n.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-gray-400 font-mono text-xs">{n.id}</td>
                      <td className="px-4 py-3 max-w-xs">
                        <div className="font-medium text-gray-800 truncate">{n.title}</div>
                        {n.is_pinned && <span className="badge bg-amber-100 text-amber-700 text-xs">📌 Pinned</span>}
                      </td>
                      <td className="px-4 py-3">
                        <CategoryBadge category={n.category} />
                      </td>
                      <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                        {n.class_name || <span className="text-gray-300">All</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{n.year}</td>
                      <td className="px-4 py-3">
                        {n.public_url
                          ? <a href={n.public_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full hover:bg-emerald-100 transition-colors">✓ YES</a>
                          : <span className="inline-flex items-center text-xs font-semibold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">✗ NO</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{n.view_count ?? 0}</td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{n.download_count ?? 0}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        {n.expires_at
                          ? <span className={`badge text-xs ${isExpired ? 'bg-red-100 text-red-600' : 'bg-amber-100 text-amber-700'}`}>
                              {isExpired ? '⏰ Expired' : new Date(n.expires_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })}
                            </span>
                          : <span className="text-xs text-gray-300">None</span>}
                      </td>
                      <td className="px-4 py-3">
                        {n.is_visible
                          ? <span className="badge text-xs bg-emerald-100 text-emerald-700">Visible</span>
                          : <span className="badge text-xs bg-amber-100 text-amber-700">Hidden</span>}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1 flex-wrap">
                          <button onClick={() => openEdit(n)}         className="text-xs font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors">Edit</button>
                          <button onClick={() => toggleVisible(n)}    className="text-xs font-medium text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded-lg hover:bg-indigo-50 transition-colors">{n.is_visible ? 'Hide' : 'Publish'}</button>
                          <button onClick={() => togglePin(n)}        className="text-xs font-medium text-amber-600 hover:text-amber-800 px-2 py-1 rounded-lg hover:bg-amber-50 transition-colors">{n.is_pinned ? 'Unpin' : 'Pin'}</button>
                          <button onClick={() => setDeleteId(n.id)}   className="text-xs font-medium text-red-500 hover:text-red-700 px-2 py-1 rounded-lg hover:bg-red-50 transition-colors">Delete</button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Upload Modal ── */}
      {showUpload && (
        <Modal title="Upload Official Notice" onClose={() => !formLoading && setShowUpload(false)}>
          <form onSubmit={handleUpload} className="space-y-4">

            <FormField label="Title" required error={formErrors.title}>
              <input name="title" value={form.title} onChange={handleFormChange} className={formErrors.title ? inputErrCls : inputCls} placeholder="e.g. 2026 Public Exam Timetable" />
            </FormField>

            <div className="grid grid-cols-2 gap-4">
              <FormField label="Category" required error={formErrors.category}>
                <select name="category" value={form.category} onChange={handleFormChange} className={formErrors.category ? inputErrCls : inputCls}>
                  <option value="">Select category…</option>
                  {NOTICE_CATEGORIES.map(c => <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>)}
                </select>
              </FormField>
              <FormField label="Year" required>
                <select name="year" value={form.year} onChange={handleFormChange} className={inputCls}>
                  {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </FormField>
            </div>

            <FormField label="Class" hint="Leave blank if applicable to all classes">
              <select name="classId" value={form.classId} onChange={handleFormChange} className={inputCls}>
                <option value="">All Classes</option>
                {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
              </select>
            </FormField>

            <FormField label="Description" hint="Optional — brief details about this notice">
              <textarea name="description" value={form.description} onChange={handleFormChange} rows={3} className={inputCls} placeholder="Optional description…" />
            </FormField>

            <FormField label="Expiry Date" hint="Optional — notice will auto-hide from public after this date">
              <input name="expiresAt" type="date" value={form.expiresAt} onChange={handleFormChange} className={inputCls} min={new Date().toISOString().slice(0, 10)} />
            </FormField>

            <FormField
              label="YouTube Video / Shorts URL"
              hint="Optional — paste a YouTube link to embed a video on the notice page"
              error={formErrors.youtubeUrl}
            >
              <input
                name="youtubeUrl"
                type="url"
                value={form.youtubeUrl}
                onChange={handleFormChange}
                className={formErrors.youtubeUrl ? inputErrCls : inputCls}
                placeholder="https://youtu.be/... or https://youtube.com/watch?v=..."
              />
            </FormField>

            <FormField
              label="File"
              required
              hint="PDF, images (JPG/PNG), Word, Excel, PowerPoint — Max 50 MB"
              error={formErrors.file}
            >
              <label className={`block cursor-pointer ${form.file ? 'border-indigo-400 bg-indigo-50' : formErrors.file ? 'border-red-300 bg-red-50' : 'border-dashed'} ${inputCls} py-3 text-center`}>
                <input name="file" type="file" accept={ACCEPTED_EXTENSIONS} onChange={handleFormChange} className="sr-only" />
                {form.file
                  ? <span className="text-indigo-700 font-medium">📎 {form.file.name} <span className="text-indigo-400 text-xs">({(form.file.size / 1024).toFixed(0)} KB)</span></span>
                  : <span className={formErrors.file ? 'text-red-400' : 'text-gray-400'}>Click to choose a file</span>}
              </label>
            </FormField>

            {uploadProgress !== null && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-indigo-600">Uploading…</span>
                  <span className="text-xs text-indigo-600">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div className="bg-indigo-600 h-2 rounded-full transition-all duration-200" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            )}

            {formErrors._general && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">{formErrors._general}</div>
            )}

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={() => setShowUpload(false)} disabled={formLoading} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button type="submit" disabled={formLoading} className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors">
                {formLoading ? <><span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Uploading…</> : 'Upload Notice'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Edit Modal ── */}
      {editNotice && (
        <Modal title="Edit Notice" onClose={() => setEditNotice(null)}>
          <form onSubmit={handleEdit} className="space-y-4">

            <FormField label="Title" required>
              <input value={editForm.title} onChange={e => setEditForm(f => ({ ...f, title: e.target.value }))} className={inputCls} placeholder="Notice title…" />
            </FormField>

            <div className="grid grid-cols-2 gap-4">
              <FormField label="Category" required>
                <select value={editForm.category} onChange={e => setEditForm(f => ({ ...f, category: e.target.value }))} className={inputCls}>
                  {NOTICE_CATEGORIES.map(c => <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>)}
                </select>
              </FormField>
              <FormField label="Year" required>
                <select value={editForm.year} onChange={e => setEditForm(f => ({ ...f, year: e.target.value }))} className={inputCls}>
                  {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </FormField>
            </div>

            <FormField label="Class" hint="Leave blank for all classes">
              <select value={editForm.classId} onChange={e => setEditForm(f => ({ ...f, classId: e.target.value }))} className={inputCls}>
                <option value="">All Classes</option>
                {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
              </select>
            </FormField>

            <FormField label="Description">
              <textarea value={editForm.description} onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))} rows={3} className={inputCls} placeholder="Optional description…" />
            </FormField>

            <FormField label="Expiry Date" hint="Clear the date to remove expiry">
              <input type="date" value={editForm.expiresAt} onChange={e => setEditForm(f => ({ ...f, expiresAt: e.target.value }))} className={inputCls} />
            </FormField>

            <FormField
              label="YouTube Video / Shorts URL"
              hint="Optional — paste a YouTube link to embed a video on the notice page"
            >
              <input
                type="url"
                value={editForm.youtubeUrl}
                onChange={e => setEditForm(f => ({ ...f, youtubeUrl: e.target.value }))}
                className={inputCls}
                placeholder="https://youtu.be/... or https://youtube.com/watch?v=..."
              />
            </FormField>

            {/* Visibility */}
            <FormField label="Visibility">
              <div className="flex gap-3">
                {[{ val: true, label: '✅ Visible' }, { val: false, label: '🙈 Hidden' }].map(o => (
                  <label key={String(o.val)} className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 cursor-pointer text-sm font-medium transition-colors ${editForm.isVisible === o.val ? 'border-indigo-500 bg-indigo-50 text-indigo-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                    <input type="radio" checked={editForm.isVisible === o.val} onChange={() => setEditForm(f => ({ ...f, isVisible: o.val }))} className="sr-only" />
                    {o.label}
                  </label>
                ))}
              </div>
            </FormField>

            {/* Pinned */}
            <FormField label="Pin Status" hint="Pinned notices appear at the top and on the home page banner.">
              <div className="flex gap-3">
                {[{ val: true, label: '📌 Pinned' }, { val: false, label: '📄 Normal' }].map(o => (
                  <label key={String(o.val)} className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 cursor-pointer text-sm font-medium transition-colors ${editForm.isPinned === o.val ? 'border-amber-400 bg-amber-50 text-amber-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                    <input type="radio" checked={editForm.isPinned === o.val} onChange={() => setEditForm(f => ({ ...f, isPinned: o.val }))} className="sr-only" />
                    {o.label}
                  </label>
                ))}
              </div>
            </FormField>

            {editError && <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">{editError}</div>}
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={() => setEditNotice(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button type="submit" disabled={editLoading} className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors">
                {editLoading ? <><span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Saving…</> : 'Save Changes'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Delete Confirm ── */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center">
            <div className="text-5xl mb-4">🗑️</div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Delete Notice?</h3>
            <p className="text-sm text-gray-500 mb-6">This will permanently remove the notice and its file. This cannot be undone.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button onClick={handleDelete} className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-xl transition-colors">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
