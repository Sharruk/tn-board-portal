import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Fetch paginated list of registered users for Admin User Management.
 */
export async function getAdminUsers({ search = '', limit = 50, offset = 0 } = {}) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (search.trim()) {
    params.append('search', search.trim())
  }

  return apiFetch(`/api/v1/admin/users?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Fetch full user detail view with contribution history, stats, and conversations.
 */
export async function getAdminUserDetail(firebaseUid) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch(`/api/v1/admin/users/${firebaseUid}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}
