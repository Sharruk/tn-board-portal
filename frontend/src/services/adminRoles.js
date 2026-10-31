import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

/**
 * Fetch authenticated administrator identity and verified privileges.
 * Also atomically resolves and claims any pending pre-authorization on login.
 */
export async function getAdminMe() {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch('/api/v1/admin/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Fetch list of all active administrators (Super Admin only).
 */
export async function getAdminList() {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch('/api/v1/admin/roles/admins', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Fetch list of all pending email pre-authorizations (Super Admin only).
 */
export async function getPendingAppointments() {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch('/api/v1/admin/roles/pending', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Pre-authorize an email address as Admin (Method 2 — Super Admin only).
 */
export async function preauthorizeAdmin(email) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch('/api/v1/admin/roles/preauthorize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ email }),
  })
}

/**
 * Revoke a pending email pre-authorization before sign-in (Super Admin only).
 */
export async function revokePendingAppointment(appointmentId) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch(`/api/v1/admin/roles/pending/${appointmentId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

/**
 * Promote an existing registered user to Admin (Method 1 — Super Admin only).
 */
export async function promoteUserToAdmin(firebaseUid) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch('/api/v1/admin/roles/promote-user', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ firebase_uid: firebaseUid }),
  })
}

/**
 * Revoke an Admin's privileges and safely restore their previous role (Super Admin only).
 */
export async function revokeAdminRole(firebaseUid) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Admin authentication required')

  return apiFetch(`/api/v1/admin/roles/revoke/${firebaseUid}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })
}

