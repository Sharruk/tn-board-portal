import { useEffect, useState, useCallback } from 'react'
import {
  getAdminStudyMaterials,
  createAdminStudyMaterial,
  updateAdminStudyMaterial,
  updateAdminStudyMaterialStatus,
  permanentlyDeleteStudyMaterial,
  MATERIAL_MEDIUMS,
  QUESTION_FORMATS,
  MATERIAL_STATUS_LABELS,
} from '../../services/studyMaterials'
import {
  getAdminMaterialCategories,
  createAdminMaterialCategory,
  updateAdminMaterialCategory,
  deleteAdminMaterialCategory,
  reactivateAdminMaterialCategory,
} from '../../services/materialCategories'
import { getClasses, getSubjectsForClass } from '../../services/classes'
import { useAdminAuth } from '../../contexts/AdminAuthContext'

function Toast({ message, type, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 4000)
    return () => clearTimeout(t)
  }, [onDismiss])
  const colors = type === 'success' ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
  return (
    <div className={`fixed bottom-6 right-6 z-[60] flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl ${colors} max-w-sm`}>
      <span className="text-lg">{type === 'success' ? '✅' : '❌'}</span>
      <p className="text-sm font-medium flex-1">{message}</p>
      <button onClick={onDismiss} className="ml-2 opacity-70 hover:opacity-100 text-lg leading-none">×</button>
    </div>
  )
}

export default function StudyMaterialsPage() {
  const { isSuperAdmin } = useAdminAuth()
  const [activeTab, setActiveTab] = useState('list') // 'list' | 'upload' | 'categories'
  const [toast, setToast] = useState(null)

  // Classes & Subjects cache
  const [classes, setClasses] = useState([])
  const [subjectsMap, setSubjectsMap] = useState({}) // { [classId]: subjects[] }

  // Materials list state
  const [materials, setMaterials] = useState([])
  const [loading, setLoading] = useState(true)
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)

  // Filters
  const [statusFilter, setStatusFilter] = useState('all')
  const [classFilter, setClassFilter] = useState('')
  const [subjectFilter, setSubjectFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  // Categories cache for dropdowns
  const [categories, setCategories] = useState([])

  // Upload/Edit Form state
  const [editingMaterial, setEditingMaterial] = useState(null)
  const [formScope, setFormScope] = useState('subject') // 'general' | 'subject'
  const [formClassId, setFormClassId] = useState('')
  const [formSubjectId, setFormSubjectId] = useState('')
  const [formCategoryId, setFormCategoryId] = useState('')
  const [formTitle, setFormTitle] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formMedium, setFormMedium] = useState('both')
  const [formQuestionFormats, setFormQuestionFormats] = useState([])
  const [formTags, setFormTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [formAcademicYear, setFormAcademicYear] = useState('')
  const [formAuthorName, setFormAuthorName] = useState('')
  const [formAuthorOrg, setFormAuthorOrg] = useState('')
  const [formFiles, setFormFiles] = useState([]) // Array of File objects
  const [formDownloadFilename, setFormDownloadFilename] = useState('')
  const [isFilenameCustomized, setIsFilenameCustomized] = useState(false)
  const [formExternalUrl, setFormExternalUrl] = useState('')
  const [formExternalTitle, setFormExternalTitle] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Category Manager modal state
  const [catModalOpen, setCatModalOpen] = useState(false)
  const [catEditing, setCatEditing] = useState(null)
  const [catName, setCatName] = useState('')
  const [catClassId, setCatClassId] = useState('')
  const [catSubjectId, setCatSubjectId] = useState('')
  const [catDesc, setCatDesc] = useState('')
  const [catOrder, setCatOrder] = useState(0)
  const [isSubmittingCategory, setIsSubmittingCategory] = useState(false)

  const showToast = (message, type = 'success') => setToast({ message, type })

  // Initial load: classes & categories
  useEffect(() => {
    getClasses().then(res => setClasses(res.data || [])).catch(() => {})
    loadCategories()
  }, [])

  const loadCategories = useCallback(async () => {
    try {
      const res = await getAdminMaterialCategories()
      setCategories(res.data || [])
    } catch {
      // Fallback
    }
  }, [])

  // When class changes in form or filter, load subjects
  const loadSubjectsForClass = useCallback(async (cid) => {
    if (!cid || subjectsMap[cid]) return
    try {
      const res = await getSubjectsForClass(cid)
      setSubjectsMap(prev => ({ ...prev, [cid]: res.data || [] }))
    } catch {
      // silent
    }
  }, [subjectsMap])

  useEffect(() => {
    if (classFilter) loadSubjectsForClass(classFilter)
    if (formClassId) loadSubjectsForClass(formClassId)
  }, [classFilter, formClassId, loadSubjectsForClass])

  // Fetch materials listing
  const fetchMaterials = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getAdminStudyMaterials({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        class_id: classFilter || undefined,
        subject_id: subjectFilter || undefined,
        category_id: categoryFilter || undefined,
        search: searchQuery || undefined,
        page,
        limit: 20,
      })
      setMaterials(res.data || [])
      setTotalCount(res.total || 0)
    } catch (err) {
      showToast(err.message || 'Failed to load materials', 'error')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, classFilter, subjectFilter, categoryFilter, searchQuery, page])

  useEffect(() => {
    if (activeTab === 'list') {
      fetchMaterials()
    }
  }, [fetchMaterials, activeTab])

  // Reset form
  const resetForm = () => {
    setEditingMaterial(null)
    setFormScope('subject')
    setFormClassId('')
    setFormSubjectId('')
    setFormCategoryId('')
    setFormTitle('')
    setFormDescription('')
    setFormMedium('both')
    setFormQuestionFormats([])
    setFormTags([])
    setTagInput('')
    setFormAcademicYear('')
    setFormAuthorName('')
    setFormAuthorOrg('')
    setFormFiles([])
    setFormDownloadFilename('')
    setIsFilenameCustomized(false)
    setFormExternalUrl('')
    setFormExternalTitle('')
  }

  const startEdit = (mat) => {
    setEditingMaterial(mat)
    setFormScope(mat.subject_id ? 'subject' : 'general')
    setFormClassId(mat.class_id ? String(mat.class_id) : '')
    setFormSubjectId(mat.subject_id ? String(mat.subject_id) : '')
    setFormCategoryId(mat.category_id ? String(mat.category_id) : '')
    setFormTitle(mat.title || '')
    setFormDescription(mat.description || '')
    setFormMedium(mat.medium || 'both')
    setFormQuestionFormats(mat.question_formats || [])
    setFormTags(mat.tags || [])
    setFormAcademicYear(mat.academic_year || '')
    setFormAuthorName(mat.author_name || '')
    setFormAuthorOrg(mat.author_organization || '')
    setFormFiles([])
    const existingFilename = mat.files?.[0]?.display_filename || ''
    setFormDownloadFilename(existingFilename)
    setIsFilenameCustomized(Boolean(existingFilename))
    setFormExternalUrl('')
    setFormExternalTitle('')
    setActiveTab('upload')
  }

  // Handle Form Submit (Draft or Publish)
  const handleSaveMaterial = async (targetStatus) => {
    if (!formTitle.trim()) {
      showToast('Title is required', 'error')
      return
    }
    if (!formClassId) {
      showToast('Please select a class standard', 'error')
      return
    }
    if (formScope === 'subject' && !formSubjectId) {
      showToast('Please select a subject for subject-specific materials', 'error')
      return
    }

    setIsSubmitting(true)
    try {
      if (editingMaterial) {
        // Update existing metadata
        await updateAdminStudyMaterial(editingMaterial.id, {
          title: formTitle.trim(),
          description: formDescription.trim() || null,
          class_id: parseInt(formClassId, 10),
          subject_id: formScope === 'subject' ? parseInt(formSubjectId, 10) : null,
          category_id: formCategoryId ? parseInt(formCategoryId, 10) : null,
          medium: formMedium,
          question_formats: formQuestionFormats,
          tags: formTags,
          academic_year: formAcademicYear.trim() || null,
          author_name: formAuthorName.trim() || null,
          author_organization: formAuthorOrg.trim() || null,
          download_filename: formDownloadFilename.trim() || null,
          status: targetStatus,
        })
        showToast(`Material updated successfully (${targetStatus})`)
        resetForm()
        setActiveTab('list')
      } else {
        // Create new
        const formData = new FormData()
        const payload = {
          title: formTitle.trim(),
          description: formDescription.trim() || null,
          class_id: parseInt(formClassId, 10),
          subject_id: formScope === 'subject' ? parseInt(formSubjectId, 10) : null,
          category_id: formCategoryId ? parseInt(formCategoryId, 10) : null,
          medium: formMedium,
          question_formats: formQuestionFormats,
          tags: formTags,
          academic_year: formAcademicYear.trim() || null,
          author_name: formAuthorName.trim() || null,
          author_organization: formAuthorOrg.trim() || null,
          download_filename: formDownloadFilename.trim() || null,
          status: targetStatus,
          files: [],
        }

        if (formExternalUrl.trim()) {
          payload.files.push({
            file_title: formExternalTitle.trim() || 'External Learning Resource',
            display_filename: formExternalTitle.trim() || 'External Resource',
            file_type: 'video',
            external_url: formExternalUrl.trim(),
          })
        }

        formData.append('payload', JSON.stringify(payload))
        formFiles.forEach(f => {
          formData.append('files', f)
        })

        await createAdminStudyMaterial(formData)
        showToast(`Material created successfully as ${targetStatus}`)
        resetForm()
        setActiveTab('list')
      }
    } catch (err) {
      showToast(err.message || 'Operation failed', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Quick Status Toggle (Draft <-> Published <-> Archived)
  const handleStatusChange = async (matId, newStatus) => {
    try {
      await updateAdminStudyMaterialStatus(matId, newStatus)
      showToast(`Status changed to ${newStatus}`)
      fetchMaterials()
    } catch (err) {
      showToast(err.message || 'Failed to update status', 'error')
    }
  }

  // Permanent Delete (Super Admin only)
  const handleDelete = async (matId, title) => {
    if (!window.confirm(`Are you sure you want to permanently delete "${title}" and all its attachments? This cannot be undone.`)) {
      return
    }
    try {
      await permanentlyDeleteStudyMaterial(matId)
      showToast('Material permanently deleted')
      fetchMaterials()
    } catch (err) {
      showToast(err.message || 'Delete failed', 'error')
    }
  }

  // Category Scope filtering for upload form
  const availableCategoriesForForm = categories.filter(c => {
    if (!c.is_active && c.id !== parseInt(formCategoryId, 10)) return false
    // Global
    if (!c.class_id && !c.subject_id) return true
    // Class-scoped
    if (formClassId && c.class_id === parseInt(formClassId, 10) && !c.subject_id) return true
    // Subject-scoped
    if (formScope === 'subject' && formSubjectId && c.subject_id === parseInt(formSubjectId, 10)) return true
    return false
  })

  // Tag chip handlers
  const handleAddTag = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      const val = tagInput.trim().replace(/^#/, '').toLowerCase()
      if (val && !formTags.includes(val)) {
        setFormTags([...formTags, val])
      }
      setTagInput('')
    }
  }

  const handleRemoveTag = (tag) => {
    setFormTags(formTags.filter(t => t !== tag))
  }

  // Category Management Handlers
  const openNewCategoryModal = () => {
    setCatEditing(null)
    setCatName('')
    setCatClassId(formClassId || '')
    setCatSubjectId(formScope === 'subject' ? formSubjectId : '')
    setCatDesc('')
    setCatOrder(categories.length + 1)
    setCatModalOpen(true)
  }

  const handleSaveCategory = async () => {
    if (isSubmittingCategory) return
    if (!catName.trim()) {
      showToast('Category name is required', 'error')
      return
    }
    setIsSubmittingCategory(true)
    try {
      if (catEditing) {
        await updateAdminMaterialCategory(catEditing.id, {
          name: catName.trim(),
          description: catDesc.trim() || null,
          display_order: parseInt(catOrder, 10) || 0,
        })
        showToast('Category updated')
      } else {
        await createAdminMaterialCategory({
          name: catName.trim(),
          description: catDesc.trim() || null,
          class_id: catClassId ? parseInt(catClassId, 10) : null,
          subject_id: catSubjectId ? parseInt(catSubjectId, 10) : null,
          display_order: parseInt(catOrder, 10) || 0,
          is_active: true,
        })
        showToast('Category created')
      }
      setCatModalOpen(false)
      loadCategories()
    } catch (err) {
      showToast(err.message || 'Category action failed', 'error')
    } finally {
      setIsSubmittingCategory(false)
    }
  }

  const handleDeleteCategory = async (cat) => {
    if (!window.confirm(`Permanently delete category "${cat.name}"? It is not used by any study materials.`)) {
      return
    }
    try {
      const res = await deleteAdminMaterialCategory(cat.id)
      showToast(res.message || 'Category deleted')
      loadCategories()
    } catch (err) {
      showToast(err.message || 'Failed to delete category', 'error')
    }
  }

  const handleArchiveCategory = async (cat) => {
    if (!window.confirm(`Archive category "${cat.name}"? It is currently used by ${cat.material_count} material(s). It will be hidden from new uploads but remain attached to existing materials.`)) {
      return
    }
    try {
      const res = await deleteAdminMaterialCategory(cat.id)
      showToast(res.message || 'Category archived')
      loadCategories()
    } catch (err) {
      showToast(err.message || 'Failed to archive category', 'error')
    }
  }

  const handleReactivateCategory = async (cat) => {
    try {
      const res = await reactivateAdminMaterialCategory(cat.id)
      showToast(res.message || 'Category reactivated')
      loadCategories()
    } catch (err) {
      showToast(err.message || 'Failed to reactivate category', 'error')
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {toast && <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Study Materials Management</h1>
          <p className="text-sm text-gray-500 mt-1">Manage notes, formulas, guides, and multi-file educational resources</p>
        </div>

        {/* Top Segmented Tabs */}
        <div className="flex bg-gray-100 p-1 rounded-xl">
          <button
            onClick={() => { setActiveTab('list'); resetForm(); }}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'list' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            All Materials ({totalCount})
          </button>
          <button
            onClick={() => { setActiveTab('upload'); resetForm(); }}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'upload' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {editingMaterial ? 'Edit Material' : '+ Upload Material'}
          </button>
          <button
            onClick={() => setActiveTab('categories')}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === 'categories' ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Categories ({categories.length})
          </button>
        </div>
      </div>

      {/* ── TAB 1: ALL MATERIALS TABLE ────────────────────────────────────────── */}
      {activeTab === 'list' && (
        <div className="space-y-6">
          {/* Filters Bar */}
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <input
              type="text"
              placeholder="Search title, description..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <select
              value={classFilter}
              onChange={e => { setClassFilter(e.target.value); setSubjectFilter(''); }}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Classes</option>
              {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select
              value={subjectFilter}
              onChange={e => setSubjectFilter(e.target.value)}
              disabled={!classFilter}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none disabled:bg-gray-50"
            >
              <option value="">All Subjects</option>
              {(subjectsMap[classFilter] || []).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">All Categories</option>
              {categories.map(cat => <option key={cat.id} value={cat.id}>{cat.name}</option>)}
            </select>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="all">Status: All</option>
              <option value="published">Status: Published</option>
              <option value="draft">Status: Draft</option>
              <option value="archived">Status: Archived</option>
            </select>
          </div>

          {/* Table */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            {loading ? (
              <div className="p-12 text-center text-gray-500">Loading study materials...</div>
            ) : materials.length === 0 ? (
              <div className="p-12 text-center text-gray-500">
                No study materials found matching the filters.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-gray-600 text-xs uppercase font-semibold border-b border-gray-200">
                    <tr>
                      <th className="px-5 py-3">Material Title</th>
                      <th className="px-4 py-3">Scope</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-3 py-3">Medium</th>
                      <th className="px-3 py-3">Attachments</th>
                      <th className="px-3 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {materials.map(mat => (
                      <tr key={mat.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-5 py-4">
                          <p className="font-semibold text-gray-900 line-clamp-1">{mat.title}</p>
                          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                            {mat.author_name && <span>By: {mat.author_name}</span>}
                            <span>• {mat.view_count || 0} views</span>
                            <span>• {mat.download_count || 0} downloads</span>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-xs font-medium">
                          {mat.subject_name ? (
                            <span className="text-blue-600">{mat.class_name} — {mat.subject_name}</span>
                          ) : (
                            <span className="text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full font-semibold">
                              {mat.class_name} General
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-4 text-xs text-gray-600">
                          {mat.category_name ? (
                            <span className="bg-gray-100 text-gray-800 px-2 py-0.5 rounded">
                              {mat.category_name}
                            </span>
                          ) : (
                            <span className="text-gray-400 italic">Uncategorized</span>
                          )}
                        </td>
                        <td className="px-3 py-4 text-xs uppercase font-semibold text-gray-500">
                          {mat.medium}
                        </td>
                        <td className="px-3 py-4 text-xs text-gray-600 font-medium">
                          📁 {mat.file_count || 0} file{mat.file_count !== 1 ? 's' : ''}
                        </td>
                        <td className="px-3 py-4">
                          <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-semibold ${MATERIAL_STATUS_LABELS[mat.status]?.color || 'bg-gray-100'}`}>
                            {MATERIAL_STATUS_LABELS[mat.status]?.label || mat.status}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-right space-x-2">
                          <button
                            onClick={() => startEdit(mat)}
                            className="px-2.5 py-1 text-xs font-medium bg-blue-50 text-blue-600 rounded hover:bg-blue-100 transition-colors"
                          >
                            Edit
                          </button>
                          {mat.status !== 'published' ? (
                            <button
                              onClick={() => handleStatusChange(mat.id, 'published')}
                              className="px-2.5 py-1 text-xs font-medium bg-emerald-50 text-emerald-600 rounded hover:bg-emerald-100 transition-colors"
                              title={mat.status === 'archived' ? 'Restore archived material to published' : 'Publish material'}
                            >
                              {mat.status === 'archived' ? 'Restore' : 'Publish'}
                            </button>
                          ) : (
                            <button
                              onClick={() => handleStatusChange(mat.id, 'archived')}
                              className="px-2.5 py-1 text-xs font-medium bg-rose-50 text-rose-600 rounded hover:bg-rose-100 transition-colors"
                            >
                              Archive
                            </button>
                          )}
                          {isSuperAdmin && (
                            <button
                              onClick={() => handleDelete(mat.id, mat.title)}
                              className="px-2.5 py-1 text-xs font-medium text-gray-400 hover:text-red-600 transition-colors"
                              title="Super Admin: Permanently delete"
                            >
                              Delete
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── TAB 2: UPLOAD / EDIT MATERIAL FORM ─────────────────────────────────── */}
      {activeTab === 'upload' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 max-w-4xl mx-auto">
          <h2 className="text-xl font-bold text-gray-900 mb-6">
            {editingMaterial ? `Edit: ${editingMaterial.title}` : 'Upload New Study Material'}
          </h2>

          <div className="space-y-6">
            {/* Scope Selection */}
            <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
              <label className="block text-sm font-semibold text-gray-800 mb-2">Scope of Resource</label>
              <div className="flex gap-6 mb-4">
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="radio"
                    name="scope"
                    value="subject"
                    checked={formScope === 'subject'}
                    onChange={() => setFormScope('subject')}
                    className="text-blue-600"
                  />
                  <span>Subject-Specific Resource</span>
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="radio"
                    name="scope"
                    value="general"
                    checked={formScope === 'general'}
                    onChange={() => { setFormScope('general'); setFormSubjectId(''); }}
                    className="text-blue-600"
                  />
                  <span>Class-Level General Resource (No subject)</span>
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Standard / Class *</label>
                  <select
                    value={formClassId}
                    onChange={e => { setFormClassId(e.target.value); setFormSubjectId(''); }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    required
                  >
                    <option value="">Select Class Standard</option>
                    {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                {formScope === 'subject' && (
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">Subject *</label>
                    <select
                      value={formSubjectId}
                      onChange={e => setFormSubjectId(e.target.value)}
                      disabled={!formClassId}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none disabled:bg-gray-100"
                      required
                    >
                      <option value="">Select Subject</option>
                      {(subjectsMap[formClassId] || []).map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>

            {/* Category & Title */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-1">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-gray-700">Category</label>
                  <button
                    type="button"
                    onClick={openNewCategoryModal}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    + New Category
                  </button>
                </div>
                <select
                  value={formCategoryId}
                  onChange={e => setFormCategoryId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="">(None / General Resource)</option>
                  {availableCategoriesForForm.map(cat => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name} {!cat.class_id ? '🌐' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Material Title *</label>
                <input
                  type="text"
                  placeholder="e.g. Class 10 Geometry Important Theorems Proofs Booklet"
                  value={formTitle}
                  onChange={e => {
                    const newTitle = e.target.value
                    setFormTitle(newTitle)
                    if (!isFilenameCustomized) {
                      const clean = newTitle.trim().replace(/[/\\?%*:|"<>]/g, '_')
                      setFormDownloadFilename(clean ? `${clean}.pdf` : '')
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  required
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Description / Syllabus Notes</label>
              <textarea
                rows={3}
                placeholder="Brief summary of the chapter, topics covered, or instructions..."
                value={formDescription}
                onChange={e => setFormDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            {/* Classification: Medium & Question Formats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Medium *</label>
                <select
                  value={formMedium}
                  onChange={e => setFormMedium(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  {MATERIAL_MEDIUMS.map(m => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Academic Year</label>
                <input
                  type="text"
                  placeholder="e.g. 2024-2025"
                  value={formAcademicYear}
                  onChange={e => setFormAcademicYear(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Question Formats Pill Selectors */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-2">Question Marking Formats (Optional)</label>
              <div className="flex flex-wrap gap-2">
                {QUESTION_FORMATS.map(q => {
                  const selected = formQuestionFormats.includes(q.value)
                  return (
                    <button
                      type="button"
                      key={q.value}
                      onClick={() => {
                        setFormQuestionFormats(selected
                          ? formQuestionFormats.filter(x => x !== q.value)
                          : [...formQuestionFormats, q.value])
                      }}
                      className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                        selected
                          ? 'bg-blue-600 text-white shadow-sm'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {selected ? '✓ ' : ''}{q.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Tags Input */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Tags (Type and press Enter or comma)</label>
              <div className="flex flex-wrap gap-2 p-2 border border-gray-300 rounded-lg focus-within:ring-2 focus-within:ring-blue-500">
                {formTags.map(tag => (
                  <span key={tag} className="bg-blue-50 text-blue-700 text-xs px-2.5 py-1 rounded-full flex items-center gap-1 font-medium">
                    #{tag}
                    <button type="button" onClick={() => handleRemoveTag(tag)} className="hover:text-blue-900">×</button>
                  </span>
                ))}
                <input
                  type="text"
                  placeholder={formTags.length === 0 ? "e.g. geometry, theorems, pta" : ""}
                  value={tagInput}
                  onChange={e => setTagInput(e.target.value)}
                  onKeyDown={handleAddTag}
                  className="flex-1 min-w-[120px] text-sm focus:outline-none"
                />
              </div>
            </div>

            {/* Author Attribution */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Author / Teacher Name</label>
                <input
                  type="text"
                  placeholder="e.g. S. Muthukumar, B.T. Asst"
                  value={formAuthorName}
                  onChange={e => setFormAuthorName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">School / Organization</label>
                <input
                  type="text"
                  placeholder="e.g. GHSS Madurai / TN Teachers Forum"
                  value={formAuthorOrg}
                  onChange={e => setFormAuthorOrg(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Custom Download File Name */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-800">
                  Student Download File Name (Customizable)
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setIsFilenameCustomized(false)
                    const clean = formTitle.trim().replace(/[/\\?%*:|"<>]/g, '_')
                    setFormDownloadFilename(clean ? `${clean}.pdf` : '')
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800 font-medium"
                >
                  ⚡ Auto-suggest from Title
                </button>
              </div>
              <input
                type="text"
                placeholder="e.g. 10th-English-Quarterly-Model-Question-Paper.pdf"
                value={formDownloadFilename}
                onChange={e => {
                  setIsFilenameCustomized(true)
                  setFormDownloadFilename(e.target.value)
                }}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none"
              />
              <p className="text-xs text-slate-500">
                When students click Download, their browser will save the file with this exact name. System automatically prevents double extensions (e.g. .pdf.pdf).
              </p>
            </div>

            {/* Attachments Section */}
            {!editingMaterial && (
              <div className="border-t border-gray-200 pt-6 space-y-4">
                <h3 className="text-sm font-semibold text-gray-900">Attachments (Max 5 files, 50MB each)</h3>
                <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-blue-400 transition-colors">
                  <input
                    type="file"
                    multiple
                    accept=".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.ppt,.pptx,.xls,.xlsx"
                    onChange={e => {
                      const newFiles = Array.from(e.target.files || [])
                      if (formFiles.length + newFiles.length > 5) {
                        showToast('Maximum 5 files allowed', 'error')
                        return
                      }
                      const oversized = newFiles.find(f => f.size > 50 * 1024 * 1024)
                      if (oversized) {
                        showToast(`File "${oversized.name}" exceeds the 50 MB size limit`, 'error')
                        return
                      }
                      setFormFiles([...formFiles, ...newFiles])
                    }}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <span className="text-3xl block mb-2">📁</span>
                    <span className="text-sm font-medium text-blue-600 hover:underline">Click to upload files</span>
                    <p className="text-xs text-gray-500 mt-1">PDF, Word, Excel, PowerPoint, Images</p>
                  </label>
                </div>

                {formFiles.length > 0 && (
                  <div className="space-y-2">
                    {formFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg text-sm border border-gray-200">
                        <span className="font-medium text-gray-800 line-clamp-1">{file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)</span>
                        <button
                          type="button"
                          onClick={() => setFormFiles(formFiles.filter((_, i) => i !== idx))}
                          className="text-red-600 hover:text-red-800 font-semibold text-xs ml-4"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {/* External Video / Web Link */}
                <div className="bg-blue-50 p-4 rounded-xl border border-blue-100 space-y-3">
                  <span className="text-xs font-semibold text-blue-900 block">Or Add an External Learning Resource (YouTube / Web):</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input
                      type="url"
                      placeholder="https://youtube.com/watch?v=..."
                      value={formExternalUrl}
                      onChange={e => setFormExternalUrl(e.target.value)}
                      className="px-3 py-2 border border-blue-200 rounded-lg text-sm bg-white focus:outline-none"
                    />
                    <input
                      type="text"
                      placeholder="Resource Title (e.g. Geometry Video Lesson)"
                      value={formExternalTitle}
                      onChange={e => setFormExternalTitle(e.target.value)}
                      className="px-3 py-2 border border-blue-200 rounded-lg text-sm bg-white focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={() => { resetForm(); setActiveTab('list'); }}
                className="px-5 py-2.5 rounded-xl border border-gray-300 text-sm font-semibold text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => handleSaveMaterial('draft')}
                className="px-5 py-2.5 rounded-xl bg-gray-200 text-sm font-semibold text-gray-800 hover:bg-gray-300 transition-colors disabled:opacity-50"
              >
                Save as Draft
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => handleSaveMaterial('published')}
                className="px-6 py-2.5 rounded-xl bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 shadow-md transition-colors disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : 'Publish Material'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB 3: MANAGE CATEGORIES ──────────────────────────────────────────── */}
      {activeTab === 'categories' && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-gray-900">Dynamic Material Categories</h2>
            <button
              onClick={openNewCategoryModal}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
            >
              + Create Category
            </button>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase font-semibold border-b border-gray-200">
                <tr>
                  <th className="px-5 py-3">Category Name</th>
                  <th className="px-4 py-3">Scope</th>
                  <th className="px-4 py-3">Slug</th>
                  <th className="px-3 py-3">Display Order</th>
                  <th className="px-3 py-3">Materials</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {categories.map(cat => (
                  <tr key={cat.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-semibold text-gray-900">{cat.name}</td>
                    <td className="px-4 py-3 text-xs">
                      {!cat.class_id ? (
                        <span className="bg-purple-50 text-purple-700 px-2.5 py-0.5 rounded-full font-semibold">🌐 Global</span>
                      ) : !cat.subject_id ? (
                        <span className="bg-amber-50 text-amber-700 px-2.5 py-0.5 rounded-full font-semibold">Class {cat.class_id}</span>
                      ) : (
                        <span className="bg-blue-50 text-blue-700 px-2.5 py-0.5 rounded-full font-semibold">Class {cat.class_id} — {cat.subject_name || 'Subject'}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 font-mono">{cat.slug}</td>
                    <td className="px-3 py-3 text-xs text-gray-700">{cat.display_order}</td>
                    <td className="px-3 py-3 text-xs font-semibold text-gray-700">
                      {cat.material_count || 0}
                    </td>
                    <td className="px-3 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${cat.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-200 text-gray-600'}`}>
                        {cat.is_active ? 'Active' : 'Archived'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => {
                          setCatEditing(cat)
                          setCatName(cat.name)
                          setCatClassId(cat.class_id ? String(cat.class_id) : '')
                          setCatSubjectId(cat.subject_id ? String(cat.subject_id) : '')
                          setCatDesc(cat.description || '')
                          setCatOrder(cat.display_order || 0)
                          setCatModalOpen(true)
                        }}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Edit
                      </button>
                      {cat.is_active ? (
                        (cat.material_count || 0) === 0 ? (
                          <button
                            onClick={() => handleDeleteCategory(cat)}
                            className="text-xs text-red-600 hover:underline"
                            title="Delete unused category"
                          >
                            Delete
                          </button>
                        ) : (
                          <button
                            onClick={() => handleArchiveCategory(cat)}
                            className="text-xs text-amber-600 hover:underline"
                            title="Archive category (linked to existing materials)"
                          >
                            Archive
                          </button>
                        )
                      ) : (
                        <>
                          <button
                            onClick={() => handleReactivateCategory(cat)}
                            className="text-xs text-emerald-600 hover:underline font-semibold"
                            title="Reactivate archived category"
                          >
                            Reactivate
                          </button>
                          {(cat.material_count || 0) === 0 && (
                            <button
                              onClick={() => handleDeleteCategory(cat)}
                              className="text-xs text-red-600 hover:underline ml-2"
                              title="Delete unused category permanently"
                            >
                              Delete
                            </button>
                          )}
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Category Create/Edit Modal */}
      {catModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-gray-900">
              {catEditing ? 'Edit Category' : 'Create New Category'}
            </h3>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Category Name *</label>
              <input
                type="text"
                placeholder="e.g. Geometry & Theorems"
                value={catName}
                onChange={e => setCatName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {!catEditing && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Class Scope</label>
                  <select
                    value={catClassId}
                    onChange={e => { setCatClassId(e.target.value); setCatSubjectId(''); }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
                  >
                    <option value="">Global (All Classes)</option>
                    {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Subject Scope</label>
                  <select
                    value={catSubjectId}
                    onChange={e => setCatSubjectId(e.target.value)}
                    disabled={!catClassId}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none disabled:bg-gray-100"
                  >
                    <option value="">Class-wide</option>
                    {(subjectsMap[catClassId] || []).map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Description (Optional)</label>
              <input
                type="text"
                placeholder="Brief category explanation..."
                value={catDesc}
                onChange={e => setCatDesc(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Display Order</label>
              <input
                type="number"
                value={catOrder}
                onChange={e => setCatOrder(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-100">
              <button
                type="button"
                onClick={() => setCatModalOpen(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-xl"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmittingCategory}
                onClick={handleSaveCategory}
                className="px-5 py-2 text-sm bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50"
              >
                {isSubmittingCategory ? 'Saving...' : 'Save Category'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
