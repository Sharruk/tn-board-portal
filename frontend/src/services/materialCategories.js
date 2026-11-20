import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Fetch active material categories for a given scope (public).
 * @param {Object} [params] - { class_id, subject_id }
 */
export async function getMaterialCategories({ class_id, subject_id } = {}) {
  const query = new URLSearchParams()
  if (class_id) query.set('class_id', class_id)
  if (subject_id) query.set('subject_id', subject_id)
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiFetch(`/api/v1/material-categories${qs}`)
}

/**
 * Fetch all categories including inactive ones (Admin).
 */
export async function getAdminMaterialCategories({ class_id, subject_id } = {}) {
  const token = await getFirebaseToken()
  const query = new URLSearchParams()
  if (class_id) query.set('class_id', class_id)
  if (subject_id) query.set('subject_id', subject_id)
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiFetch(`/api/v1/admin/material-categories${qs}`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

/**
 * Create a new dynamic category (Admin).
 */
export async function createAdminMaterialCategory(payload) {
  const token = await getFirebaseToken()
  return apiFetch('/api/v1/admin/material-categories', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
}

/**
 * Update an existing category (Admin).
 */
export async function updateAdminMaterialCategory(categoryId, payload) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/material-categories/${categoryId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  })
}

/**
 * Delete or soft-archive category (Admin).
 */
export async function deleteAdminMaterialCategory(categoryId) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/material-categories/${categoryId}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

/**
 * Reactivate an archived category (Admin).
 */
export async function reactivateAdminMaterialCategory(categoryId) {
  const token = await getFirebaseToken()
  return apiFetch(`/api/v1/admin/material-categories/${categoryId}/reactivate`, {
    method: 'PATCH',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}
