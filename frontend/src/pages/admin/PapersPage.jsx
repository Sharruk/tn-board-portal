import { useEffect, useState, useCallback } from 'react'
import { getAdminPapers, uploadPaper, deletePaper, updatePaper } from '../../services/admin'
import { getClasses, getSubjectsForClass } from '../../services/classes'

const EXAM_TYPES = [
  'Unit Test 1', 'Unit Test 2', 'Unit Test 3',
  'Quarterly Exam', 'Half Yearly Exam',
  'Annual Exam', 'Public Exam', 'Practical Exam', 'Model Exam',
]

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 10 }, (_, i) => CURRENT_YEAR - i)

const EMPTY_FORM = {
  classId: '', subjectId: '', examType: '', year: String(CURRENT_YEAR),
  title: '', paperType: 'question', youtubeUrl: '', file: null,
}

function extractYouTubeId(url) {
  if (!url) return null
  try {
    const u = new URL(url)
    if (u.hostname.includes('youtube.com')) return u.searchParams.get('v')
    if (u.hostname === 'youtu.be') return u.pathname.slice(1).split('?')[0]
  } catch {
    const m = url.match(/(?:v=|youtu\.be\/)([A-Za-z0-9_-]{11})/)
    return m ? m[1] : null
  }
  return null
}

function Toast({ message, type, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000)
    return () => clearTimeout(t)
  }, [onDismiss])

  const colors = type === 'success'
    ? 'bg-emerald-600 text-white'
    : 'bg-red-600 text-white'

  return (
    <div className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl ${colors} max-w-sm`}>
      <span className="text-lg">{type === 'success' ? '✅' : '❌'}</span>
      <p className="text-sm font-medium flex-1">{message}</p>
      <button onClick={onDismiss} className="ml-2 opacity-70 hover:opacity-100 text-lg leading-none">×</button>
    </div>
  )
}

function Badge({ type }) {
  return type === 'question'
    ? <span className="badge bg-blue-100 text-blue-700">Q Paper</span>
    : <span className="badge bg-green-100 text-green-700">Answer Key</span>
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded-lg hover:bg-gray-100 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
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

const inputCls = "w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-800 outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition bg-white"
const inputErrCls = "w-full px-3 py-2.5 border border-red-300 rounded-xl text-sm text-gray-800 outline-none focus:ring-2 focus:ring-red-300 focus:border-red-400 transition bg-white"

export default function PapersPage() {
  const [papers, setPapers] = useState([])
  const [classes, setClasses] = useState([])
  const [subjectsCache, setSubjectsCache] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [showUpload, setShowUpload] = useState(false)
  const [deleteId, setDeleteId] = useState(null)
  const [editPaper, setEditPaper] = useState(null)

  const [form, setForm] = useState(EMPTY_FORM)
  const [formSubjects, setFormSubjects] = useState([])
  const [formLoading, setFormLoading] = useState(false)
  const [formErrors, setFormErrors] = useState({})
  const [uploadProgress, setUploadProgress] = useState(null)

  const [editForm, setEditForm] = useState({ youtubeUrl: '', isVisible: true })
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState(null)

  const [filterClass, setFilterClass] = useState('')
  const [filterType, setFilterType] = useState('')

  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => setToast({ message, type })

  const buildSubjectMap = useCallback((cache) => {
    const map = {}
    Object.values(cache).flat().forEach(s => { map[s.id] = s })
    return map
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([getAdminPapers(), getClasses()])
      .then(([papersRes, classesRes]) => {
        setPapers(papersRes.data)
        setClasses(classesRes.data)
        const ids = classesRes.data.map(c => c.id)
        Promise.all(ids.map(id => getSubjectsForClass(id))).then(results => {
          const cache = {}
          results.forEach((r, i) => { cache[ids[i]] = r.data })
          setSubjectsCache(cache)
        })
      })
      .catch(err => setError(err.response?.data?.detail || 'Failed to load data'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const subjectMap = buildSubjectMap(subjectsCache)

  const filteredPapers = papers.filter(p => {
    const sub = subjectMap[p.subject_id]
    if (filterClass && sub?.class_id !== parseInt(filterClass)) return false
    if (filterType && p.paper_type !== filterType) return false
    return true
  })

  const handleFormClassChange = async (classId) => {
    setForm(f => ({ ...f, classId, subjectId: '' }))
    if (!classId) { setFormSubjects([]); return }
    if (subjectsCache[classId]) {
      setFormSubjects(subjectsCache[classId])
      return
    }
    const res = await getSubjectsForClass(classId)
    setSubjectsCache(c => ({ ...c, [classId]: res.data }))
    setFormSubjects(res.data)
  }

  const handleFormChange = e => {
    const { name, value, files } = e.target
    if (name === 'file') setForm(f => ({ ...f, file: files[0] || null }))
    else setForm(f => ({ ...f, [name]: value }))
    if (formErrors[name]) setFormErrors(fe => ({ ...fe, [name]: null }))
  }

  const validateForm = () => {
    const errors = {}
    if (!form.classId) errors.classId = 'Please select a class'
    if (!form.subjectId) errors.subjectId = 'Please select a subject'
    if (!form.examType) errors.examType = 'Please select an exam type'
    if (!form.title.trim()) errors.title = 'Title is required'
    return errors
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    const errors = validateForm()
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      return
    }
    setFormLoading(true)
    setFormErrors({})
    setUploadProgress(0)
    try {
      const fd = new FormData()
      fd.append('subject_id', form.subjectId)
      fd.append('exam_type', form.examType)
      fd.append('year', form.year)
      fd.append('title', form.title)
      fd.append('paper_type', form.paperType)
      if (form.youtubeUrl) fd.append('youtube_url', form.youtubeUrl)
      if (form.file) fd.append('file', form.file)
      await uploadPaper(fd, (pct) => setUploadProgress(pct))
      setShowUpload(false)
      setForm(EMPTY_FORM)
      setFormSubjects([])
      setUploadProgress(null)
      load()
      showToast('Paper uploaded successfully!')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Upload failed. Please try again.'
      setFormErrors({ _general: msg })
      setUploadProgress(null)
    } finally {
      setFormLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteId) return
    try {
      await deletePaper(deleteId)
      setDeleteId(null)
      load()
      showToast('Paper deleted.')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Delete failed', 'error')
    }
  }

  const openEdit = (paper) => {
    setEditPaper(paper)
    setEditForm({ youtubeUrl: paper.youtube_url || '', isVisible: paper.is_visible })
    setEditError(null)
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    setEditLoading(true)
    setEditError(null)
    try {
      await updatePaper(editPaper.id, {
        youtube_url: editForm.youtubeUrl || null,
        is_visible: editForm.isVisible,
      })
      setEditPaper(null)
      load()
      showToast('Paper updated successfully!')
    } catch (err) {
      setEditError(err.response?.data?.detail || 'Update failed')
    } finally {
      setEditLoading(false)
    }
  }

  const ytIdUpload = extractYouTubeId(form.youtubeUrl)
  const ytIdEdit = extractYouTubeId(editForm.youtubeUrl)

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto">
      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-extrabold text-gray-900">Papers</h1>
          <p className="text-gray-500 text-sm mt-1">
            {papers.length} paper{papers.length !== 1 ? 's' : ''} total
          </p>
        </div>
        <button
          onClick={() => { setShowUpload(true); setFormErrors({}); setForm(EMPTY_FORM); setFormSubjects([]) }}
          className="btn-primary"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Upload Paper
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select value={filterClass} onChange={e => setFilterClass(e.target.value)} className="text-sm border border-gray-200 rounded-xl px-3 py-2 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-blue-100">
          <option value="">All Classes</option>
          {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select value={filterType} onChange={e => setFilterType(e.target.value)} className="text-sm border border-gray-200 rounded-xl px-3 py-2 text-gray-700 bg-white outline-none focus:ring-2 focus:ring-blue-100">
          <option value="">All Types</option>
          <option value="question">Question Papers</option>
          <option value="answer_key">Answer Keys</option>
        </select>
        {(filterClass || filterType) && (
          <button onClick={() => { setFilterClass(''); setFilterType('') }} className="text-sm text-red-500 hover:text-red-700 font-medium px-2">Clear</button>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <span className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        ) : error ? (
          <p className="text-center py-16 text-red-500">{error}</p>
        ) : filteredPapers.length === 0 ? (
          <div className="text-center py-20 px-6">
            <div className="text-5xl mb-4">📭</div>
            <p className="text-gray-500 font-medium">
              {papers.length === 0 ? 'No papers uploaded yet.' : 'No papers match the current filters.'}
            </p>
            {papers.length === 0 && (
              <button onClick={() => setShowUpload(true)} className="mt-4 btn-primary">
                Upload First Paper
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  {['#', 'Title', 'Class / Subject', 'Exam Type', 'Year', 'PDF', 'YouTube', 'Visible', 'Actions'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filteredPapers.map(p => {
                  const sub = subjectMap[p.subject_id]
                  return (
                    <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 text-gray-400 font-mono text-xs">{p.id}</td>
                      <td className="px-4 py-3 max-w-xs">
                        <div className="font-medium text-gray-800 truncate">{p.title}</div>
                        <Badge type={p.paper_type} />
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="text-gray-800 font-medium">{sub?.class_name || `Class ?`}</div>
                        <div className="text-gray-400 text-xs">{sub?.name || `Subject #${p.subject_id}`}</div>
                      </td>
                      <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{p.exam_type}</td>
                      <td className="px-4 py-3 text-gray-600">{p.year}</td>
                      <td className="px-4 py-3">
                        {p.public_url ? (
                          <a href={p.public_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full hover:bg-emerald-100 transition-colors">
                            ✓ YES
                          </a>
                        ) : (
                          <span className="inline-flex items-center text-xs font-semibold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">✗ NO</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {p.youtube_url ? (
                          <a href={p.youtube_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full hover:bg-emerald-100 transition-colors">
                            ✓ YES
                          </a>
                        ) : (
                          <span className="inline-flex items-center text-xs font-semibold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">✗ NO</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`badge text-xs ${p.is_visible ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                          {p.is_visible ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => openEdit(p)}
                            className="text-xs font-medium text-blue-600 hover:text-blue-800 px-2 py-1 rounded-lg hover:bg-blue-50 transition-colors"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => setDeleteId(p.id)}
                            className="text-xs font-medium text-red-500 hover:text-red-700 px-2 py-1 rounded-lg hover:bg-red-50 transition-colors"
                          >
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

      {/* ── Upload Modal ── */}
      {showUpload && (
        <Modal title="Upload Paper" onClose={() => !formLoading && setShowUpload(false)}>
          <form onSubmit={handleUpload} className="space-y-4">

            <div className="grid grid-cols-2 gap-4">
              <FormField label="Class" required error={formErrors.classId}>
                <select
                  name="classId" value={form.classId}
                  onChange={e => handleFormClassChange(e.target.value)}
                  className={formErrors.classId ? inputErrCls : inputCls}
                >
                  <option value="">Select class…</option>
                  {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </FormField>
              <FormField label="Subject" required error={formErrors.subjectId}>
                <select
                  name="subjectId" value={form.subjectId} onChange={handleFormChange}
                  className={formErrors.subjectId ? inputErrCls : inputCls}
                  disabled={!form.classId}
                >
                  <option value="">Select subject…</option>
                  {formSubjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </FormField>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <FormField label="Exam Type" required error={formErrors.examType}>
                <select
                  name="examType" value={form.examType} onChange={handleFormChange}
                  className={formErrors.examType ? inputErrCls : inputCls}
                >
                  <option value="">Select type…</option>
                  {EXAM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </FormField>
              <FormField label="Year" required>
                <select name="year" value={form.year} onChange={handleFormChange} className={inputCls}>
                  {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
              </FormField>
            </div>

            <FormField label="Title" required hint="e.g. Class 10 Maths Annual Exam 2024" error={formErrors.title}>
              <input
                name="title" value={form.title} onChange={handleFormChange}
                className={formErrors.title ? inputErrCls : inputCls}
                placeholder="Paper title…"
              />
            </FormField>

            <FormField label="Paper Type" required>
              <div className="flex gap-3">
                {[{ val: 'question', label: '📝 Question Paper' }, { val: 'answer_key', label: '✅ Answer Key' }].map(o => (
                  <label key={o.val} className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 cursor-pointer text-sm font-medium transition-colors ${
                    form.paperType === o.val ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}>
                    <input type="radio" name="paperType" value={o.val} checked={form.paperType === o.val} onChange={handleFormChange} className="sr-only" />
                    {o.label}
                  </label>
                ))}
              </div>
            </FormField>

            <FormField label="YouTube URL" hint="Optional — paste a YouTube link for the explanation video">
              <input name="youtubeUrl" value={form.youtubeUrl} onChange={handleFormChange} className={inputCls} placeholder="https://youtube.com/watch?v=…" />
              {ytIdUpload && (
                <div className="mt-2 rounded-xl overflow-hidden border border-gray-200">
                  <img
                    src={`https://img.youtube.com/vi/${ytIdUpload}/mqdefault.jpg`}
                    alt="YouTube thumbnail"
                    className="w-full h-32 object-cover"
                    onError={e => { e.currentTarget.style.display = 'none' }}
                  />
                  <p className="px-3 py-1.5 text-xs text-gray-500 bg-gray-50">▶ Video preview</p>
                </div>
              )}
            </FormField>

            <FormField label="PDF File" hint="Optional — upload a PDF. Students can download it.">
              <label className={`block cursor-pointer ${inputCls} py-3 text-center ${form.file ? 'border-blue-400 bg-blue-50' : 'border-dashed'}`}>
                <input name="file" type="file" accept=".pdf,.doc,.docx" onChange={handleFormChange} className="sr-only" />
                {form.file
                  ? <span className="text-blue-700 font-medium">📄 {form.file.name} <span className="text-blue-400 text-xs">({(form.file.size / 1024).toFixed(0)} KB)</span></span>
                  : <span className="text-gray-400">Click to choose file (PDF, DOC)</span>}
              </label>
            </FormField>

            {/* Upload Progress */}
            {uploadProgress !== null && (
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-blue-600">Uploading…</span>
                  <span className="text-xs text-blue-600">{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-200"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            {formErrors._general && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">{formErrors._general}</div>
            )}

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={() => setShowUpload(false)} disabled={formLoading} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button type="submit" disabled={formLoading} className="btn-primary flex-1 justify-center">
                {formLoading ? (
                  <><span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> Uploading…</>
                ) : 'Upload Paper'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Edit Modal ── */}
      {editPaper && (
        <Modal title="Edit Paper" onClose={() => setEditPaper(null)}>
          <div className="mb-4 bg-gray-50 rounded-xl p-3">
            <p className="font-medium text-gray-800 text-sm">{editPaper.title}</p>
            <p className="text-xs text-gray-400 mt-0.5">{editPaper.exam_type} · {editPaper.year}</p>
          </div>
          <form onSubmit={handleEdit} className="space-y-4">
            <FormField label="YouTube URL" hint="Paste a YouTube URL or leave empty to remove">
              <input
                value={editForm.youtubeUrl}
                onChange={e => setEditForm(f => ({ ...f, youtubeUrl: e.target.value }))}
                className={inputCls}
                placeholder="https://youtube.com/watch?v=…"
              />
              {ytIdEdit && (
                <div className="mt-2 rounded-xl overflow-hidden border border-gray-200">
                  <img
                    src={`https://img.youtube.com/vi/${ytIdEdit}/mqdefault.jpg`}
                    alt="YouTube thumbnail"
                    className="w-full h-32 object-cover"
                    onError={e => { e.currentTarget.style.display = 'none' }}
                  />
                  <p className="px-3 py-1.5 text-xs text-gray-500 bg-gray-50">▶ Video preview</p>
                </div>
              )}
            </FormField>
            <FormField label="Visibility">
              <label className="flex items-center gap-3 cursor-pointer">
                <div
                  onClick={() => setEditForm(f => ({ ...f, isVisible: !f.isVisible }))}
                  className={`w-11 h-6 rounded-full transition-colors relative cursor-pointer ${editForm.isVisible ? 'bg-blue-600' : 'bg-gray-300'}`}
                >
                  <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${editForm.isVisible ? 'translate-x-5' : ''}`} />
                </div>
                <span className="text-sm font-medium text-gray-700">
                  {editForm.isVisible ? 'Visible to students' : 'Hidden from students'}
                </span>
              </label>
            </FormField>
            {editError && <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">{editError}</div>}
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={() => setEditPaper(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button type="submit" disabled={editLoading} className="btn-primary flex-1 justify-center">
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
            <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">🗑️</div>
            <h3 className="text-lg font-bold text-gray-900 mb-2">Delete Paper?</h3>
            <p className="text-gray-500 text-sm mb-6">This will permanently delete the paper and its file. This action cannot be undone.</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="btn-secondary flex-1 justify-center">Cancel</button>
              <button onClick={handleDelete} className="flex-1 justify-center inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-lg transition-colors">
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
