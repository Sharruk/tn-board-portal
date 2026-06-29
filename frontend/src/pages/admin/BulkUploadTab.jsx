import { useState, useCallback } from 'react'
import { uploadPaper } from '../../services/admin'
import { getSubjectsForClass } from '../../services/classes'

const EXAM_TYPES = [
  'Monthly Test',
  'Unit Test 1', 'Unit Test 2', 'Unit Test 3',
  'Quarterly Exam', 'Half Yearly Exam',
  'Annual Exam', 'Public Exam', 'Practical Exam', 'Model Exam',
]

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = Array.from({ length: 10 }, (_, i) => CURRENT_YEAR - i)

const SUBJECT_ALIASES = {
  maths: 'Mathematics', math: 'Mathematics', mathematics: 'Mathematics',
  phy: 'Physics', physics: 'Physics',
  chem: 'Chemistry', chemistry: 'Chemistry',
  bio: 'Biology', biology: 'Biology',
  eng: 'English', english: 'English',
  tamil: 'Tamil',
  cs: 'Computer Science', computer: 'Computer Science', 'computer science': 'Computer Science',
  history: 'History',
  geo: 'Geography', geography: 'Geography',
  civics: 'Civics',
  economics: 'Economics',
  commerce: 'Commerce',
  accounts: 'Accountancy', accountancy: 'Accountancy',
  social: 'Social Science', science: 'Science',
}

const EXAM_ALIASES = {
  monthly: 'Monthly Test', monthlytest: 'Monthly Test', 'monthly test': 'Monthly Test',
  annual: 'Annual Exam',
  halfyearly: 'Half Yearly Exam', 'half-yearly': 'Half Yearly Exam', 'half yearly': 'Half Yearly Exam',
  quarterly: 'Quarterly Exam',
  unittest1: 'Unit Test 1', unit1: 'Unit Test 1', 'unit test 1': 'Unit Test 1',
  unittest2: 'Unit Test 2', unit2: 'Unit Test 2', 'unit test 2': 'Unit Test 2',
  unittest3: 'Unit Test 3', unit3: 'Unit Test 3', 'unit test 3': 'Unit Test 3',
  public: 'Public Exam',
  model: 'Model Exam',
  practical: 'Practical Exam',
}

function extractMetadata(filename, classes, subjectsCache) {
  const base = filename.replace(/\.pdf$/i, '')
  const lower = base.toLowerCase()
  const normed = lower.replace(/[\s_\-]+/g, ' ')

  const classMatch = normed.match(/class\s*(\d{1,2})/)
  let classId = ''
  let classNum = null
  if (classMatch) {
    classNum = parseInt(classMatch[1])
    const found = classes.find(c => c.name === `Class ${classNum}` || c.slug === String(classNum))
    if (found) classId = String(found.id)
  }

  const yearMatch = normed.match(/\b(20\d{2})\b/)
  const year = yearMatch ? yearMatch[1] : String(CURRENT_YEAR)

  let examType = ''
  for (const [alias, full] of Object.entries(EXAM_ALIASES)) {
    if (normed.replace(/\s/g, '').includes(alias.replace(/\s/g, ''))) {
      examType = full
      break
    }
  }

  let subjectName = ''
  let subjectId = ''
  const parts = normed.split(/[\s_\-]+/)
  for (const part of parts) {
    if (SUBJECT_ALIASES[part]) {
      subjectName = SUBJECT_ALIASES[part]
      break
    }
  }
  if (!subjectName) {
    for (const [alias, full] of Object.entries(SUBJECT_ALIASES)) {
      if (normed.includes(alias)) {
        subjectName = full
        break
      }
    }
  }
  if (subjectName && classId && subjectsCache[classId]) {
    const sub = subjectsCache[classId].find(s => s.name.toLowerCase() === subjectName.toLowerCase())
    if (sub) subjectId = String(sub.id)
  }

  const titleParts = [classNum ? `Class ${classNum}` : '', subjectName, examType, year].filter(Boolean)
  const title = titleParts.join(' ') || base

  return { classId, subjectId, examType, year, title, subjectName }
}

function computeWarnings(item, allItems) {
  const warns = []
  if (!item.year) warns.push('Year is missing')
  if (item.title && item.title.trim().length < 10) warns.push('Title seems too short')
  if (item.file.size < 10240) warns.push('PDF is suspiciously small — may be corrupt or empty')
  const dupes = allItems.filter(f => f.id !== item.id && f.file.name === item.file.name)
  if (dupes.length > 0) warns.push('Duplicate filename in this batch')
  return warns
}

const inputCls = 'w-full px-2.5 py-2 border border-gray-200 rounded-lg text-sm text-gray-800 outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400 bg-white'

function StatusBadge({ status }) {
  if (status === 'done') return <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">✓ Done</span>
  if (status === 'failed') return <span className="text-xs font-semibold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">✗ Failed</span>
  if (status === 'uploading') return <span className="text-xs font-semibold text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full animate-pulse">Uploading…</span>
  return <span className="text-xs font-semibold text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">Pending</span>
}

export default function BulkUploadTab({ classes, subjectsCache, onSubjectLoad, onDone }) {
  const [items, setItems] = useState([])
  const [uploading, setUploading] = useState(false)
  const [summary, setSummary] = useState(null)

  const updateItem = (id, patch) =>
    setItems(prev => prev.map(it => it.id === id ? { ...it, ...patch } : it))

  const handleFilesChange = (e) => {
    const files = Array.from(e.target.files || [])
    const newItems = files.map(file => {
      const meta = extractMetadata(file.name, classes, subjectsCache)
      const item = {
        id: `${Date.now()}-${Math.random()}`,
        file,
        classId: meta.classId,
        subjectId: meta.subjectId,
        examType: meta.examType,
        year: meta.year,
        title: meta.title,
        paperType: 'question',
        status: 'pending',
        progress: 0,
        errorMsg: null,
      }
      return item
    })
    setItems(prev => {
      const combined = [...prev, ...newItems]
      return combined.map(it => ({ ...it, warnings: computeWarnings(it, combined) }))
    })
    e.target.value = ''
    setSummary(null)
  }

  const handleClassChange = async (id, classId) => {
    updateItem(id, { classId, subjectId: '' })
    if (classId && !subjectsCache[classId]) {
      const res = await onSubjectLoad(classId)
      setItems(prev => {
        const updated = prev.map(it => it.id === id ? { ...it, classId, subjectId: '' } : it)
        return updated.map(it => ({ ...it, warnings: computeWarnings(it, updated) }))
      })
    }
  }

  const handleFieldChange = (id, field, value) => {
    setItems(prev => {
      const updated = prev.map(it => it.id === id ? { ...it, [field]: value } : it)
      return updated.map(it => ({ ...it, warnings: computeWarnings(it, updated) }))
    })
  }

  const removeItem = (id) => {
    setItems(prev => {
      const updated = prev.filter(it => it.id !== id)
      return updated.map(it => ({ ...it, warnings: computeWarnings(it, updated) }))
    })
    setSummary(null)
  }

  const handleUploadAll = async () => {
    const pending = items.filter(it => it.status === 'pending')
    if (pending.length === 0) return
    const invalid = pending.filter(it => !it.classId || !it.subjectId || !it.examType || !it.title.trim())
    if (invalid.length > 0) {
      setItems(prev => prev.map(it =>
        invalid.find(inv => inv.id === it.id) ? { ...it, errorMsg: 'Fill in all required fields.' } : it
      ))
      return
    }

    setUploading(true)
    setSummary(null)
    let succeeded = 0
    let failed = 0

    for (const item of pending) {
      updateItem(item.id, { status: 'uploading', progress: 0, errorMsg: null })
      try {
        const fd = new FormData()
        fd.append('subject_id', item.subjectId)
        fd.append('exam_type', item.examType)
        fd.append('year', item.year)
        fd.append('title', item.title)
        fd.append('paper_type', item.paperType)
        fd.append('file', item.file)
        fd.append('is_bulk', 'true')
        // original_filename is captured from the File object — preserved through uploadPaper
        fd.append('original_filename', item.file.name)
        await uploadPaper(fd, (pct) => updateItem(item.id, { progress: pct }))
        updateItem(item.id, { status: 'done', progress: 100 })
        succeeded++
      } catch (err) {
        const msg = err.message || 'Upload failed'
        updateItem(item.id, { status: 'failed', errorMsg: msg })
        failed++
      }
    }

    setUploading(false)
    setSummary({ succeeded, failed })
    if (succeeded > 0) onDone()
  }

  const pendingCount = items.filter(it => it.status === 'pending').length
  const doneCount = items.filter(it => it.status === 'done').length
  const failedCount = items.filter(it => it.status === 'failed').length

  return (
    <div className="space-y-6">
      {/* Drop zone */}
      <label className="flex flex-col items-center justify-center w-full h-36 border-2 border-dashed border-blue-300 rounded-2xl bg-blue-50 hover:bg-blue-100 cursor-pointer transition-colors">
        <input type="file" accept=".pdf" multiple onChange={handleFilesChange} className="sr-only" disabled={uploading} />
        <svg xmlns="http://www.w3.org/2000/svg" className="w-10 h-10 text-blue-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
        </svg>
        <p className="text-sm font-semibold text-blue-700">Click to select multiple PDFs</p>
        <p className="text-xs text-blue-400 mt-1">Select as many files as you need — they will be queued below</p>
      </label>

      {/* Summary banner */}
      {summary && (
        <div className={`rounded-xl px-5 py-3 text-sm font-medium flex items-center gap-3 ${summary.failed === 0 ? 'bg-emerald-50 border border-emerald-200 text-emerald-800' : 'bg-amber-50 border border-amber-200 text-amber-800'}`}>
          <span className="text-lg">{summary.failed === 0 ? '🎉' : '⚠️'}</span>
          <span>
            Upload complete — <strong>{summary.succeeded}</strong> succeeded
            {summary.failed > 0 && <>, <strong>{summary.failed}</strong> failed</>}
          </span>
        </div>
      )}

      {/* File list */}
      {items.length === 0 ? (
        <div className="text-center py-10 text-gray-400">
          <div className="text-4xl mb-2">📂</div>
          <p className="text-sm">No files selected yet. Use the button above to add PDFs.</p>
        </div>
      ) : (
        <>
          {/* Header row */}
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-gray-700">
              {items.length} file{items.length !== 1 ? 's' : ''} queued
              {doneCount > 0 && <span className="text-emerald-600 ml-2">· {doneCount} done</span>}
              {failedCount > 0 && <span className="text-red-500 ml-1">· {failedCount} failed</span>}
            </p>
            <div className="flex items-center gap-3">
              {!uploading && items.some(it => it.status === 'pending') && (
                <button
                  onClick={() => setItems(prev => prev.filter(it => it.status === 'done'))}
                  className="text-xs text-gray-400 hover:text-red-500 font-medium transition-colors"
                >
                  Clear pending
                </button>
              )}
              <button
                onClick={handleUploadAll}
                disabled={uploading || pendingCount === 0}
                className="btn-primary text-sm px-5 py-2"
              >
                {uploading
                  ? <><span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin inline-block mr-2" />Uploading…</>
                  : `Upload All (${pendingCount})`}
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {items.map(item => {
              const subjects = subjectsCache[item.classId] || []
              return (
                <div key={item.id} className={`bg-white border rounded-2xl overflow-hidden shadow-sm ${item.status === 'done' ? 'border-emerald-200' : item.status === 'failed' ? 'border-red-200' : 'border-gray-200'}`}>
                  {/* File header */}
                  <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-100">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-blue-500 text-lg shrink-0">📄</span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{item.file.name}</p>
                        <p className="text-xs text-gray-400">{(item.file.size / 1024).toFixed(0)} KB</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 ml-4 shrink-0">
                      <StatusBadge status={item.status} />
                      {item.status === 'pending' && !uploading && (
                        <button onClick={() => removeItem(item.id)} className="text-gray-300 hover:text-red-400 transition-colors text-lg leading-none">×</button>
                      )}
                    </div>
                  </div>

                  {/* Progress bar (during upload) */}
                  {item.status === 'uploading' && (
                    <div className="px-4 pt-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-blue-600 font-medium">Uploading…</span>
                        <span className="text-xs text-blue-600">{item.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-1.5">
                        <div className="bg-blue-500 h-1.5 rounded-full transition-all duration-150" style={{ width: `${item.progress}%` }} />
                      </div>
                    </div>
                  )}

                  {/* Error message */}
                  {item.errorMsg && (
                    <div className="mx-4 mt-3 bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-600 font-medium">{item.errorMsg}</div>
                  )}

                  {/* Warnings */}
                  {item.warnings && item.warnings.length > 0 && item.status === 'pending' && (
                    <div className="mx-4 mt-3 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 space-y-0.5">
                      {item.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-amber-700 font-medium">⚠ {w}</p>
                      ))}
                    </div>
                  )}

                  {/* Fields */}
                  {item.status !== 'done' && (
                    <div className="p-4 grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-gray-500 mb-1">Class <span className="text-red-400">*</span></label>
                        <select value={item.classId} onChange={e => handleClassChange(item.id, e.target.value)} className={inputCls} disabled={uploading}>
                          <option value="">Select class…</option>
                          {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-500 mb-1">Subject <span className="text-red-400">*</span></label>
                        <select value={item.subjectId} onChange={e => handleFieldChange(item.id, 'subjectId', e.target.value)} className={inputCls} disabled={!item.classId || uploading}>
                          <option value="">Select subject…</option>
                          {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-500 mb-1">Exam Type <span className="text-red-400">*</span></label>
                        <select value={item.examType} onChange={e => handleFieldChange(item.id, 'examType', e.target.value)} className={inputCls} disabled={uploading}>
                          <option value="">Select type…</option>
                          {EXAM_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-500 mb-1">Year</label>
                        <select value={item.year} onChange={e => handleFieldChange(item.id, 'year', e.target.value)} className={inputCls} disabled={uploading}>
                          {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                        </select>
                      </div>
                      <div className="col-span-2">
                        <label className="block text-xs font-semibold text-gray-500 mb-1">Title <span className="text-red-400">*</span></label>
                        <input value={item.title} onChange={e => handleFieldChange(item.id, 'title', e.target.value)} className={inputCls} placeholder="Paper title…" disabled={uploading} />
                      </div>
                      <div className="col-span-2">
                        <label className="block text-xs font-semibold text-gray-500 mb-1">Type</label>
                        <div className="flex gap-2">
                          {[{ val: 'question', label: '📝 Question Paper' }, { val: 'answer_key', label: '✅ Answer Key' }].map(o => (
                            <label key={o.val} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border-2 cursor-pointer text-xs font-medium transition-colors ${item.paperType === o.val ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-500 hover:border-gray-300'}`}>
                              <input type="radio" value={o.val} checked={item.paperType === o.val} onChange={() => handleFieldChange(item.id, 'paperType', o.val)} className="sr-only" disabled={uploading} />
                              {o.label}
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
