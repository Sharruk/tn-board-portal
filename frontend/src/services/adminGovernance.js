import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Add an Administrator (Super Admin or Verified Teacher).
 */
export async function addAdmin({ email, display_name, reason }) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch('/api/v1/admin/governance/add', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ email, display_name, reason }),
  })
}

/**
 * Request removal of an Administrator.
 */
export async function requestAdminRemoval({ target_uid, reason }) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch('/api/v1/admin/governance/removal-request', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ target_uid, reason }),
  })
}

/**
 * List governance requests (pending, approved, rejected).
 */
export async function getGovernanceRequests(params = {}) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  const query = new URLSearchParams()
  if (params.status) query.set('status', params.status)
  if (params.request_type) query.set('request_type', params.request_type)
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))

  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiFetch(`/api/v1/admin/governance/requests${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

/**
 * Approve an Admin removal request (two-person rule).
 */
export async function approveRemovalRequest(requestId, note = null) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/admin/governance/requests/${requestId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ note }),
  })
}

/**
 * Reject an Admin removal request.
 */
export async function rejectRemovalRequest(requestId, note = null) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/admin/governance/requests/${requestId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ note }),
  })
}

/**
 * Super Admin: Grant or revoke Verified Teacher status.
 */
export async function updateVerifiedTeacherStatus(firebaseUid, isVerifiedTeacher) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/admin/users/${firebaseUid}/verified-teacher`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ is_verified_teacher: isVerifiedTeacher }),
  })
}

/**
 * Fetch immutable admin activity logs.
 */
export async function getAdminActivity(params = {}) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  const query = new URLSearchParams()
  if (params.action) query.set('action', params.action)
  if (params.target_type) query.set('target_type', params.target_type)
  if (params.limit) query.set('limit', String(params.limit))
  if (params.offset) query.set('offset', String(params.offset))

  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiFetch(`/api/v1/admin/activity${qs}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}
