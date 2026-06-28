import { useEffect, useState, useCallback } from 'react'
import {
  getAdminNews,
  createNews,
  updateNews,
  deleteNews,
  uploadNewsFile,
  deleteNewsFile,
  generateSlug,
  NEWS_CATEGORIES,
  NEWS_CATEGORY_ICONS,
  NEWS_STATUS_LABELS,
  formatPublishedDate,
} from '../../services/news'
import { isValidYouTubeUrl } from '../../services/notices'
import { getClasses } from '../../services/classes'

// ── Constants ─────────────────────────────────────────────────────────────────

const CURRENT_YEAR = new Date().getFullYear()
const CLASSES = [9, 10, 11, 12]

const EMPTY_FORM = {
  title: '', slug: '', summary: '', content: '', category: '',
  tags: '', thumbnail: null, thumbnailAlt: '', youtubeUrl: '',
  pdf: null, classId: '', district: '', publishedAt: '', status: 'draft', isPinned: false,
}

const ACCEPTED_IMAGE = '.jpg,.jpeg,.png,.webp,.gif'
const ACCEPTED_PDF   = '.pdf'

// ── Shared UI sub-components ──────────────────────────────────────────────────

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={onClose} role="dialog" aria-modal="true">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col" style={{ maxHeight: '90vh' }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors" aria-label="Close">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="overflow-y-auto overscroll-contain px-6 py-5 flex-1 min-h-0">{children}</div>
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

function ProgressBar({ pct }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-indigo-600">Uploading…</span>
        <span className="text-xs text-indigo-600">{pct}%</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div className="bg-indigo-600 h-2 rounded-full transition-all duration-200" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

// ── News form — shared between create and edit ────────────────────────────────

function NewsForm({ initial, onSubmit, onClose, submitLabel, loading: submitting }) {
  const [form, setForm]       = useState(initial)
  const [errors, setErrors]   = useState({})
  const [thumbPreview, setThumbPreview] = useState(initial.existingThumbUrl || null)
  const [uploadPct, setUploadPct]       = useState(null)

  const set = (key, val) => {
    setForm(f => ({ ...f, [key]: val }))
    if (errors[key]) setErrors(e => ({ ...e, [key]: null }))
  }

  // Auto-generate slug from title (only when slug is not manually edited)
  const [slugManual, setSlugManual] = useState(!!initial.slug)
  const handleTitleChange = (v) => {
    set('title', v)
    if (!slugManual) set('slug', generateSlug(v))
  }

  const handleThumbChange = (e) => {
    const f = e.target.files[0] || null
    set('thumbnail', f)
    if (f) setThumbPreview(URL.createObjectURL(f))
    else setThumbPreview(initial.existingThumbUrl || null)
  }

  const validate = () => {
    const errs = {}
    if (!form.title.trim())     errs.title    = 'Title is required'
    if (!form.slug.trim())      errs.slug     = 'Slug is required'
    if (!form.category)         errs.category = 'Please select a category'
    if (!form.summary?.trim())  errs.summary  = 'Summary is required'
    if (form.youtubeUrl && !isValidYouTubeUrl(form.youtubeUrl))
      errs.youtubeUrl = 'Enter a valid YouTube URL (youtu.be, youtube.com/watch?v=, or youtube.com/shorts/)'
    return errs
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    await onSubmit(form, setUploadPct)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Title */}
      <FormField label="Title" required error={errors.title}>
        <input
          value={form.title}
          onChange={e => handleTitleChange(e.target.value)}
          className={errors.title ? inputErrCls : inputCls}
          placeholder="e.g. Heavy Rain Holiday — Schools Closed in Chennai"
        />
      </FormField>

      {/* Slug */}
      <FormField label="Slug (URL)" required hint="Used in the article URL: /news/your-slug" error={errors.slug}>
        <input
          value={form.slug}
          onChange={e => { setSlugManual(true); set('slug', generateSlug(e.target.value)) }}
          className={errors.slug ? inputErrCls : inputCls}
          placeholder="heavy-rain-holiday-chennai"
        />
        {form.slug && (
          <p className="mt-1 text-xs text-indigo-600 font-mono">/news/{form.slug}</p>
        )}
      </FormField>

      {/* Category + Status */}
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Category" required error={errors.category}>
          <select value={form.category} onChange={e => set('category', e.target.value)} className={errors.category ? inputErrCls : inputCls}>
            <option value="">Select category…</option>
            {NEWS_CATEGORIES.map(c => <option key={c} value={c}>{NEWS_CATEGORY_ICONS[c]} {c}</option>)}
          </select>
        </FormField>
        <FormField label="Status">
          <select value={form.status} onChange={e => set('status', e.target.value)} className={inputCls}>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        </FormField>
      </div>

      {/* Summary */}
      <FormField label="Summary" required hint="Short excerpt shown in cards and search results" error={errors.summary}>
        <textarea
          value={form.summary}
          onChange={e => set('summary', e.target.value)}
          rows={2}
          className={errors.summary ? inputErrCls : inputCls}
          placeholder="Brief description of the article…"
        />
      </FormField>

      {/* Content */}
      <FormField label="Full Article Content" hint="Use blank lines to separate paragraphs">
        <textarea
          value={form.content}
          onChange={e => set('content', e.target.value)}
          rows={8}
          className={inputCls}
          placeholder="Write the full article here…"
        />
      </FormField>

      {/* Thumbnail */}
      <FormField label="Thumbnail Image" hint="JPG, PNG, WEBP — Max 20 MB">
        {thumbPreview && (
          <div className="mb-2 rounded-xl overflow-hidden border border-gray-200 bg-gray-50" style={{ maxHeight: 160 }}>
            <img src={thumbPreview} alt="Preview" className="w-full object-cover" style={{ maxHeight: 160 }} />
          </div>
        )}
        <label className={`block cursor-pointer ${form.thumbnail ? 'border-indigo-400 bg-indigo-50' : 'border-dashed'} ${inputCls} py-3 text-center`}>
          <input type="file" accept={ACCEPTED_IMAGE} onChange={handleThumbChange} className="sr-only" />
          {form.thumbnail
            ? <span className="text-indigo-700 font-medium">📎 {form.thumbnail.name}</span>
            : <span className="text-gray-400">{thumbPreview ? 'Click to replace image' : 'Click to choose image'}</span>}
        </label>
      </FormField>

      {/* Thumbnail Alt */}
      <FormField label="Thumbnail Alt Text" hint="For accessibility and SEO">
        <input
          value={form.thumbnailAlt}
          onChange={e => set('thumbnailAlt', e.target.value)}
          className={inputCls}
          placeholder="Brief description of the image"
        />
      </FormField>

      {/* YouTube + PDF */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField label="YouTube URL (Optional)" hint="Supports youtu.be, watch?v=, /shorts/" error={errors.youtubeUrl}>
          <input
            type="url"
            value={form.youtubeUrl}
            onChange={e => set('youtubeUrl', e.target.value)}
            className={errors.youtubeUrl ? inputErrCls : inputCls}
            placeholder="https://youtu.be/..."
          />
        </FormField>
        <FormField label="PDF Attachment (Optional)" hint="PDF only — Max 20 MB">
          <label className={`block cursor-pointer ${form.pdf ? 'border-indigo-400 bg-indigo-50' : 'border-dashed'} ${inputCls} py-3 text-center`}>
            <input type="file" accept={ACCEPTED_PDF} onChange={e => set('pdf', e.target.files[0] || null)} className="sr-only" />
            {form.pdf
              ? <span className="text-indigo-700 font-medium text-sm">📎 {form.pdf.name}</span>
              : <span className="text-gray-400 text-sm">{initial.existingPdfUrl ? 'Click to replace PDF' : 'Click to choose PDF'}</span>}
          </label>
          {initial.existingPdfUrl && !form.pdf && (
            <a href={initial.existingPdfUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-indigo-600 hover:underline mt-1 block">
              📄 View existing PDF
            </a>
          )}
        </FormField>
      </div>

      {/* Class + District */}
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Applicable Class" hint="Leave blank for all classes">
          <select value={form.classId} onChange={e => set('classId', e.target.value)} className={inputCls}>
            <option value="">All Classes</option>
            {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
          </select>
        </FormField>
        <FormField label="District (Optional)">
          <input
            value={form.district}
            onChange={e => set('district', e.target.value)}
            className={inputCls}
            placeholder="e.g. Chennai, Coimbatore…"
          />
        </FormField>
      </div>

      {/* Tags */}
      <FormField label="Tags (Optional)" hint="Comma-separated: rain, holiday, chennai">
        <input
          value={form.tags}
          onChange={e => set('tags', e.target.value)}
          className={inputCls}
          placeholder="rain, holiday, government"
        />
      </FormField>

      {/* Publish Date + Pin */}
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Publish Date" hint="Leave blank to publish immediately when status is Published">
          <input
            type="datetime-local"
            value={form.publishedAt}
            onChange={e => set('publishedAt', e.target.value)}
            className={inputCls}
          />
        </FormField>
        <FormField label="Pin Status" hint="Pinned articles appear at the top">
          <div className="flex gap-3 mt-1">
            {[{ val: true, label: '📌 Pinned' }, { val: false, label: '📄 Normal' }].map(o => (
              <label
                key={String(o.val)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 cursor-pointer text-sm font-medium transition-colors ${
                  form.isPinned === o.val ? 'border-amber-400 bg-amber-50 text-amber-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                <input type="radio" checked={form.isPinned === o.val} onChange={() => set('isPinned', o.val)} className="sr-only" />
                {o.label}
              </label>
            ))}
          </div>
        </FormField>
      </div>

      {/* Upload progress */}
      {uploadPct !== null && <ProgressBar pct={uploadPct} />}

      {/* Error general */}
      {errors._general && (
        <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">{errors._general}</div>
      )}

      <div className="flex gap-3 pt-2">
        <button type="button" onClick={onClose} disabled={submitting} className="btn-secondary flex-1 justify-center">Cancel</button>
        <button type="submit" disabled={submitting} className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors">
          {submitting ? <><span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Saving…</> : submitLabel}
        </button>
      </div>
    </form>
  )
}

// =============================================================================
// Main AdminNewsPage
// =============================================================================

export default function AdminNewsPage() {
  const [articles, setArticles] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [toast, setToast]       = useState(null)

  const [showCreate, setShowCreate] = useState(false)
  const [editArticle, setEditArticle] = useState(null)
  const [deleteId, setDeleteId]       = useState(null)

  const [createLoading, setCreateLoading] = useState(false)
  const [editLoading, setEditLoading]     = useState(false)

  // Filters
  const [filterCategory, setFilterCategory] = useState('')
  const [filterStatus, setFilterStatus]     = useState('')

  const showToast = (message, type = 'success') => setToast({ message, type })

  const load = useCallback(() => {
    setLoading(true)
    getAdminNews()
      .then(res => setArticles(res.data))
      .catch(err => setError(err.message || 'Failed to load news'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = articles.filter(a => {
    if (filterCategory && a.category !== filterCategory) return false
    if (filterStatus   && a.status   !== filterStatus)   return false
    return true
  })

  // ── Create handler ───────────────────────────────────────────────────────────

  const handleCreate = async (form, setProgress) => {
    setCreateLoading(true)
    try {
      let thumbnailUrl = null
      let pdfUrl       = null

      // Upload thumbnail
      if (form.thumbnail) {
        setProgress(10)
        const res = await uploadNewsFile(form.thumbnail, p => setProgress(Math.round(10 + p * 0.4)))
        thumbnailUrl = res.publicUrl
      }
      setProgress(50)

      // Upload PDF
      if (form.pdf) {
        const res = await uploadNewsFile(form.pdf, p => setProgress(Math.round(50 + p * 0.4)))
        pdfUrl = res.publicUrl
      }
      setProgress(92)

      const tags = form.tags
        ? form.tags.split(',').map(t => t.trim()).filter(Boolean)
        : []

      const payload = {
        title:         form.title.trim(),
        slug:          form.slug.trim(),
        summary:       form.summary?.trim() || null,
        content:       form.content?.trim() || null,
        category:      form.category,
        tags,
        thumbnail_url: thumbnailUrl,
        thumbnail_alt: form.thumbnailAlt?.trim() || null,
        youtube_url:   form.youtubeUrl?.trim() || null,
        pdf_url:       pdfUrl,
        class_id:      form.classId ? parseInt(form.classId, 10) : null,
        district:      form.district?.trim() || null,
        status:        form.status,
        is_pinned:     form.isPinned,
        published_at:  form.publishedAt
          ? new Date(form.publishedAt).toISOString()
          : form.status === 'published' ? new Date().toISOString() : null,
      }

      await createNews(payload)
      setShowCreate(false)
      load()
      setProgress(100)
      showToast('Article created successfully!')
    } catch (err) {
      showToast(err.message || 'Failed to create article', 'error')
    } finally {
      setCreateLoading(false)
    }
  }

  // ── Edit handler ──────────────────────────────────────────────────────────────

  const handleEdit = async (form, setProgress) => {
    if (!editArticle) return
    setEditLoading(true)
    try {
      let thumbnailUrl = editArticle.thumbnail_url
      let pdfUrl       = editArticle.pdf_url

      // Replace thumbnail
      if (form.thumbnail) {
        setProgress(10)
        if (editArticle.thumbnail_url) await deleteNewsFile(editArticle.thumbnail_url)
        const res = await uploadNewsFile(form.thumbnail, p => setProgress(Math.round(10 + p * 0.4)))
        thumbnailUrl = res.publicUrl
      }
      setProgress(50)

      // Replace PDF
      if (form.pdf) {
        if (editArticle.pdf_url) await deleteNewsFile(editArticle.pdf_url)
        const res = await uploadNewsFile(form.pdf, p => setProgress(Math.round(50 + p * 0.4)))
        pdfUrl = res.publicUrl
      }
      setProgress(90)

      const tags = form.tags
        ? form.tags.split(',').map(t => t.trim()).filter(Boolean)
        : []

      const updates = {
        title:         form.title.trim(),
        slug:          form.slug.trim(),
        summary:       form.summary?.trim() || null,
        content:       form.content?.trim() || null,
        category:      form.category,
        tags,
        thumbnail_url: thumbnailUrl,
        thumbnail_alt: form.thumbnailAlt?.trim() || null,
        youtube_url:   form.youtubeUrl?.trim() || null,
        pdf_url:       pdfUrl,
        class_id:      form.classId ? parseInt(form.classId, 10) : null,
        district:      form.district?.trim() || null,
        status:        form.status,
        is_pinned:     form.isPinned,
        published_at:  form.publishedAt
          ? new Date(form.publishedAt).toISOString()
          : (form.status === 'published' && !editArticle.published_at ? new Date().toISOString() : editArticle.published_at),
      }

      await updateNews(editArticle.id, updates)
      setEditArticle(null)
      load()
      showToast('Article updated successfully!')
    } catch (err) {
      showToast(err.message || 'Failed to update article', 'error')
    } finally {
      setEditLoading(false)
    }
  }

  // ── Delete handler ────────────────────────────────────────────────────────────

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deleteNews(deleteId)
      setDeleteId(null)
      load()
      showToast('Article deleted.')
    } catch (err) {
      showToast(err.message || 'Delete failed', 'error')
    }
  }

  // ── Quick-action helpers ──────────────────────────────────────────────────────

  const quickStatus = async (a, newStatus) => {
    try {
      const updates = { status: newStatus }
      if (newStatus === 'published' && !a.published_at) updates.published_at = new Date().toISOString()
      await updateNews(a.id, updates)
      load()
      showToast(newStatus === 'published' ? 'Article published!' : newStatus === 'archived' ? 'Article archived.' : 'Article set to draft.')
    } catch (err) {
      showToast(err.message || 'Failed', 'error')
    }
  }

  const quickPin = async (a) => {
    try {
      await updateNews(a.id, { is_pinned: !a.is_pinned })
      load()
      showToast(a.is_pinned ? 'Article unpinned.' : 'Article pinned!')
    } catch (err) {
      showToast(err.message || 'Failed', 'error')
    }
  }

  // Build initial state for edit form
  const buildEditInitial = (a) => ({
    title:          a.title || '',
    slug:           a.slug || '',
    summary:        a.summary || '',
    content:        a.content || '',
    category:       a.category || '',
    tags:           (a.tags || []).join(', '),
    thumbnail:      null,
    thumbnailAlt:   a.thumbnail_alt || '',
    youtubeUrl:     a.youtube_url || '',
    pdf:            null,
    classId:        a.class_id ? String(a.class_id) : '',
    district:       a.district || '',
    publishedAt:    a.published_at ? a.published_at.slice(0, 16) : '',
    status:         a.status || 'draft',
    isPinned:       a.is_pinned ?? false,
    existingThumbUrl: a.thumbnail_url || null,
    existingPdfUrl:   a.pdf_url || null,
  })

  // ==========================================================================
  // Render
  // ==========================================================================

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">News &amp; Updates</h1>
          <p className="text-gray-500 text-sm mt-1">{articles.length} article{articles.length !== 1 ? 's' : ''} total</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Create Article
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select value={filterCategory} onChange={e => setFilterCategory(e.target.value)} className="text-sm border border-gray-200 rounded-xl px-3 py-2 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-100">
          <option value="">All Categories</option>
          {NEWS_CATEGORIES.map(c => <option key={c} value={c}>{NEWS_CATEGORY_ICONS[c]} {c}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="text-sm border border-gray-200 rounded-xl px-3 py-2 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-indigo-100">
          <option value="">All Status</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
        {(filterCategory || filterStatus) && (
          <button onClick={() => { setFilterCategory(''); setFilterStatus('') }} className="text-sm text-red-500 hover:text-red-700 font-medium px-2">
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
              {articles.length === 0 ? 'No articles yet.' : 'No articles match the current filters.'}
            </p>
            {articles.length === 0 && (
              <button onClick={() => setShowCreate(true)} className="mt-4 btn-primary">Create First Article</button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['Thumbnail', 'Title', 'Category', 'Status', 'Pinned', 'Published', 'Views', 'Actions'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map(a => {
                  const statusMeta = NEWS_STATUS_LABELS[a.status] || NEWS_STATUS_LABELS.draft
                  return (
                    <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        {a.thumbnail_url
                          ? <img src={a.thumbnail_url} alt={a.thumbnail_alt || a.title} className="w-12 h-9 rounded-lg object-cover" />
                          : <div className="w-12 h-9 rounded-lg bg-gray-100 flex items-center justify-center text-xl">{NEWS_CATEGORY_ICONS[a.category] ?? '📰'}</div>}
                      </td>
                      <td className="px-4 py-3 max-w-xs">
                        <div className="font-medium text-gray-800 truncate">{a.title}</div>
                        <div className="text-xs text-gray-400 font-mono truncate">/news/{a.slug}</div>
                        {a.youtube_url && <span className="badge bg-red-100 text-red-700 text-xs mt-0.5">▶ Video</span>}
                      </td>
                      <td className="px-4 py-3">
                        <span className="badge bg-indigo-50 text-indigo-700 text-xs">{NEWS_CATEGORY_ICONS[a.category]} {a.category}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`badge text-xs ${statusMeta.color}`}>{statusMeta.label}</span>
                      </td>
                      <td className="px-4 py-3">
                        {a.is_pinned
                          ? <span className="badge bg-amber-100 text-amber-700 text-xs">📌 Yes</span>
                          : <span className="text-xs text-gray-300">—</span>}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                        {a.published_at ? formatPublishedDate(a.published_at, { short: true }) : <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{a.view_count ?? 0}</td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1 flex-wrap">
                          <button onClick={() => setEditArticle(a)} className="text-xs font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors">
                            Edit
                          </button>
                          {a.status !== 'published' && (
                            <button onClick={() => quickStatus(a, 'published')} className="text-xs font-medium text-emerald-600 hover:text-emerald-800 px-2 py-1 rounded-lg hover:bg-emerald-50 transition-colors">
                              Publish
                            </button>
                          )}
                          {a.status === 'published' && (
                            <button onClick={() => quickStatus(a, 'archived')} className="text-xs font-medium text-gray-600 hover:text-gray-800 px-2 py-1 rounded-lg hover:bg-gray-100 transition-colors">
                              Archive
                            </button>
                          )}
                          {a.status !== 'draft' && (
                            <button onClick={() => quickStatus(a, 'draft')} className="text-xs font-medium text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded-lg hover:bg-indigo-50 transition-colors">
                              Draft
                            </button>
                          )}
                          <button onClick={() => quickPin(a)} className="text-xs font-medium text-amber-600 hover:text-amber-800 px-2 py-1 rounded-lg hover:bg-amber-50 transition-colors">
                            {a.is_pinned ? 'Unpin' : 'Pin'}
                          </button>
                          <button onClick={() => setDeleteId(a.id)} className="text-xs font-medium text-red-500 hover:text-red-700 px-2 py-1 rounded-lg hover:bg-red-50 transition-colors">
                            Delete
                          </button>
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

      {/* ── Create Modal ── */}
      {showCreate && (
        <Modal title="Create News Article" onClose={() => !createLoading && setShowCreate(false)}>
          <NewsForm
            initial={EMPTY_FORM}
            onSubmit={handleCreate}
            onClose={() => setShowCreate(false)}
            submitLabel="Create Article"
            loading={createLoading}
          />
        </Modal>
      )}

      {/* ── Edit Modal ── */}
      {editArticle && (
        <Modal title="Edit News Article" onClose={() => !editLoading && setEditArticle(null)}>
          <NewsForm
            initial={buildEditInitial(editArticle)}
            onSubmit={handleEdit}
            onClose={() => setEditArticle(null)}
            submitLabel="Save Changes"
            loading={editLoading}
          />
        </Modal>
      )}

      {/* ── Delete Confirm ── */}
      {deleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center">
            <div className="text-5xl mb-4">🗑️</div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Delete Article?</h3>
            <p className="text-sm text-gray-500 mb-6">This will permanently remove the article, its thumbnail, and any PDF attachment. This cannot be undone.</p>
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
