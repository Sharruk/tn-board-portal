import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

export const MATERIAL_MEDIUMS = [
  { value: 'both', label: 'All Mediums (Tamil & English)' },
  { value: 'tamil', label: 'Tamil Medium (தமிழ் வழி)' },
  { value: 'english', label: 'English Medium' },
  { value: 'not_applicable', label: 'Not Applicable / Universal' },
]

export const QUESTION_FORMATS = [
  { value: '1_mark', label: '1 Mark' },
  { value: '2_marks', label: '2 Marks' },
  { value: '3_marks', label: '3 Marks' },
  { value: '5_marks', label: '5 Marks' },
  { value: '10_marks', label: '10 Marks' },
]

export const MATERIAL_STATUS_LABELS = {
  draft:     { label: 'Draft',     color: 'bg-gray-100 text-gray-700' },
  published: { label: 'Published', color: 'bg-emerald-100 text-emerald-800' },
  archived:  { label: 'Archived',  color: 'bg-rose-100 text-rose-800' },
}

/**
 * Public: List published study materials with filters & search.
 */
export async function getStudyMaterials({
  class_id,
  subject_id,
  category_id,
  medium,
  tag,
  question_format,
  search,
  page = 1,
  limit = 20,
} = {}) {
  const query = new URLSearchParams()
  if (class_id) query.set('class_id', class_id)
  if (subject_id) query.set('subject_id', subject_id)
  if (category_id) query.set('category_id', category_id)
  if (medium && medium !== 'all') query.set('medium', medium)
  if (tag) query.set('tag', tag)
  if (question_format) query.set('question_format', question_format)
  if (search) query.set('search', search)
  query.set('page', page)
  query.set('limit', limit)

  return apiFetch(`/api/v1/study-materials?${query.toString()}`)
}

/**
 * Public: Get published material detail by slug.
 */
export async function getStudyMaterialBySlug(slug) {
  return apiFetch(`/api/v1/study-materials/${encodeURIComponent(slug)}`)
}

/**
 * Public: Get published materials for a specific subject (for the SubjectPage tab).
 */
export async function getMaterialsBySubject(subjectId, { category_id, medium, tag, page = 1, limit = 50 } = {}) {
  const query = new URLSearchParams()
  if (category_id) query.set('category_id', category_id)
  if (medium && medium !== 'all') query.set('medium', medium)
  if (tag) query.set('tag', tag)
  query.set('page', page)
  query.set('limit', limit)

  return apiFetch(`/api/v1/study-materials/by-subject/${subjectId}?${query.toString()}`)
}

/**
 * Public: Get class-level general materials (subject_id IS NULL).
 */
export async function getClassGeneralMaterials(classId, { category_id, medium, page = 1, limit = 20 } = {}) {
  const query = new URLSearchParams()
  if (category_id) query.set('category_id', category_id)
  if (medium && medium !== 'all') query.set('medium', medium)
  query.set('page', page)
  query.set('limit', limit)

  return apiFetch(`/api/v1/study-materials/class-general/${classId}?${query.toString()}`)
}

/**
 * Public: Track download and get download URL.
 */
export async function downloadMaterialFile(materialId, fileId) {
  const token = await getFirebaseToken().catch(() => null)
  return apiFetch(`/api/v1/study-materials/${materialId}/files/${fileId}/download`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

// ── Admin Functions ──────────────────────────────────────────────────────────

/**
 * Admin: List all materials with status filter and search.
 */
export async function getAdminStudyMaterials({
  status,
  class_id,
  subject_id,
  category_id,
  search,
  page = 1,
  limit = 50,
} = {}) {
  const token = await getFirebaseToken()
  const query = new URLSearchParams()
  if (status && status !== 'all') query.set('status', status)
  if (class_id) query.set('class_id', class_id)
  if (subject_id) query.set('subject_id', subject_id)
  if (category_id) query.set('category_id', category_id)
  if (search) query.set('search', search)
  query.set('page', page)
  query.set('limit', limit)

  return apiFetch(`/api/v1/admin/study-materials?${query.toString()}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

/**
 * Admin: Get material detail for editing.
 */
export async function getAdminStudyMaterial(id) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/study-materials/${id}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

/**
 * Admin: Create study material with attachments via FormData.
 */
export async function createAdminStudyMaterial(formData) {
  const token = await getFirebaseToken()
  return apiFetch('/api/v1/admin/study-materials', {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })
}

/**
 * Admin: Update study material metadata.
 */
export async function updateAdminStudyMaterial(id, payload) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/study-materials/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
}

/**
 * Admin: Change publication status (draft, published, archived).
 */
export async function updateAdminStudyMaterialStatus(id, status) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/study-materials/${id}/status`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ status }),
  })
}

/**
 * Admin: Add single attachment or external link to existing material.
 */
export async function addAdminAttachment(materialId, formData) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/study-materials/${materialId}/files`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  })
}

/**
 * Admin: Delete single attachment.
 */
export async function deleteAdminAttachment(materialId, fileId) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/study-materials/${materialId}/files/${fileId}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

/**
 * Super Admin: Permanently delete study material and purge files.
 */
export async function permanentlyDeleteStudyMaterial(id) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/study-materials/${id}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

// ── Likes & Comments Functions ───────────────────────────────────────────────

/**
 * Toggle study material like (auth required).
 */
export async function toggleMaterialLike(materialId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to like')

  return apiFetch(`/api/v1/study-materials/${materialId}/like`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Get study material likes status and count.
 */
export async function getMaterialLikes(materialId) {
  const token = await getFirebaseToken().catch(() => null)
  const headers = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  return apiFetch(`/api/v1/study-materials/${materialId}/likes`, { headers })
}

/**
 * Get study material threaded comments.
 */
export async function getMaterialComments(materialId) {
  return apiFetch(`/api/v1/study-materials/${materialId}/comments`)
}

/**
 * Add a comment/reply to a study material.
 */
export async function addMaterialComment(materialId, payload) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to comment')

  return apiFetch(`/api/v1/study-materials/${materialId}/comments`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
}

/**
 * Delete a study material comment.
 */
export async function deleteMaterialComment(commentId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to delete comment')

  return apiFetch(`/api/v1/study-materials/comments/${commentId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

