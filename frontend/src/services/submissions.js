// =============================================================================
// Submissions Service — frontend/src/services/submissions.js
// =============================================================================
// API calls for the material submission feature.
//
// Public:
//   createSubmission(formData)  — POST /api/v1/submissions  (multipart)
//
// Admin (requires Firebase token in Authorization header):
//   getSubmissions(token, status)               — GET  /api/v1/submissions
//   getSubmission(token, id)                    — GET  /api/v1/submissions/{id}
//   approveSubmission(token, id, body)           — POST /api/v1/submissions/{id}/approve
//   rejectSubmission(token, id, body)            — POST /api/v1/submissions/{id}/reject
//   restoreSubmission(token, id)                 — POST /api/v1/submissions/{id}/restore
//   downloadSubmissionFile(token, fileId)        — GET  /api/v1/submissions/files/{fileId}/download
// =============================================================================

import { apiFetch } from '../lib/api'
import { getFirebaseToken } from '../lib/firebase'

function getApiUrl(path) {
  const envUrl = import.meta.env.VITE_API_BASE_URL || ''
  if (envUrl.includes('onrender.com') || envUrl.includes('render.com')) {
    return path
  }
  if (typeof window !== 'undefined' && (window.location.hostname.endsWith('vercel.app') || window.location.hostname === 'tn-board-portal.vercel.app')) {
    return path
  }
  return `${envUrl}${path}`
}

/**
 * Submit educational material (requires auth).
 *
 * @param {FormData} formData  Must include: publisher_name, files[].
 *                             Optional: details.
 * @returns {Promise<{ id: string, status: string, message: string }>}
 */
export async function createSubmission(formData) {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to submit material')

  // We use raw fetch here (not apiFetch) because we need multipart/form-data
  // without setting Content-Type manually — the browser sets boundary automatically.
  const url = getApiUrl('/api/v1/submissions')
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    headers: {
      'Authorization': `Bearer ${token}`
    }
    // DO NOT set Content-Type — browser sets it with correct boundary
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      detail = body?.detail || body?.message || detail
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail)
  }

  return response.json()
}

// ── Contributor: Get authenticated user's own submissions ────────────────────


/**
 * Fetch all submissions submitted by the current authenticated user.
 * @returns {Promise<{ data: UserSubmissionItem[], total: number }>}
 */
export async function getMySubmissions() {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')
  return apiFetch('/api/v1/submissions/my', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

// ── Admin: List submissions ───────────────────────────────────────────────────

/**
 * List all submissions (admin only).
 *
 * Supports both getSubmissions(statusFilter, limit) and legacy getSubmissions(token, statusFilter, limit).
 *
 * @param {string|null} [tokenOrStatusFilter]  statusFilter ('pending' | 'approved' | 'rejected' | null) or legacy token
 * @param {string|number|null} [statusFilterOrLimit]
 * @param {number} [maybeLimit]  Max results (default 50)
 * @returns {Promise<{ data: SubmissionListItem[], count: number, status_filter: string|null }>}
 */
export async function getSubmissions(tokenOrStatusFilter = null, statusFilterOrLimit = null, maybeLimit = 50) {
  let statusFilter = null
  let limit = 50

  if (typeof tokenOrStatusFilter === 'string' && (tokenOrStatusFilter.startsWith('ey') || tokenOrStatusFilter.length > 50)) {
    statusFilter = statusFilterOrLimit
    limit = typeof maybeLimit === 'number' ? maybeLimit : 50
  } else {
    statusFilter = tokenOrStatusFilter
    limit = typeof statusFilterOrLimit === 'number' ? statusFilterOrLimit : 50
  }

  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  const params = new URLSearchParams({ limit: String(limit) })
  if (statusFilter) params.set('status', statusFilter)
  return apiFetch(`/api/v1/submissions?${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

// ── Admin: Get submission detail ──────────────────────────────────────────────

/**
 * Get a single submission with its file list (admin only).
 *
 * Supports both getSubmission(id) and legacy getSubmission(token, id).
 *
 * @param {string} tokenOrId  Submission UUID or legacy token
 * @param {string} [maybeId]  Submission UUID if token was passed first
 * @returns {Promise<SubmissionOut>}
 */
export async function getSubmission(tokenOrId, maybeId) {
  const id = maybeId !== undefined ? maybeId : tokenOrId
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/submissions/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

// ── Admin: Approve submission ─────────────────────────────────────────────────

/**
 * Approve a pending submission and create paper record(s).
 * Obtains a fresh Firebase ID token immediately before sending the mutation request.
 *
 * Supports both approveSubmission(id, body) and legacy approveSubmission(token, id, body).
 *
 * @param {string} tokenOrId  Submission UUID or legacy token
 * @param {string|object} idOrBody Submission UUID or body object
 * @param {object} [maybeBody] Body if token was passed as first argument
 * @returns {Promise<{ submission_id: string, status: string, paper_ids: number[] }>}
 */
export async function approveSubmission(tokenOrId, idOrBody, maybeBody) {
  let id, body
  if (maybeBody !== undefined) {
    id = idOrBody
    body = maybeBody
  } else {
    id = tokenOrId
    body = idOrBody
  }

  const token = await getFirebaseToken(true)
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/submissions/${id}/approve`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}

// ── Admin: Reject submission ──────────────────────────────────────────────────

/**
 * Reject a pending submission.
 * Obtains a fresh Firebase ID token immediately before sending the mutation request.
 *
 * Supports both rejectSubmission(id, body) and legacy rejectSubmission(token, id, body).
 *
 * @param {string} tokenOrId  Submission UUID or legacy token
 * @param {string|object} idOrBody Submission UUID or body object
 * @param {object} [maybeBody] Body if token was passed as first argument
 * @returns {Promise<{ submission_id: string, status: string, rejection_reason: string|null }>}
 */
export async function rejectSubmission(tokenOrId, idOrBody, maybeBody) {
  let id, body
  if (maybeBody !== undefined) {
    id = idOrBody
    body = maybeBody
  } else {
    id = tokenOrId
    body = idOrBody
  }

  const token = await getFirebaseToken(true)
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/submissions/${id}/reject`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
}

// ── Admin: Restore rejected submission to pending ─────────────────────────────

/**
 * Restore a rejected submission back to pending.
 * Obtains a fresh Firebase ID token immediately before sending the mutation request.
 *
 * Supports both restoreSubmission(id) and legacy restoreSubmission(token, id).
 *
 * @param {string} tokenOrId  Submission UUID or legacy token
 * @param {string} [maybeId]  Submission UUID if token was passed first
 * @returns {Promise<{ submission_id: string, status: string }>}
 */
export async function restoreSubmission(tokenOrId, maybeId) {
  const id = maybeId !== undefined ? maybeId : tokenOrId
  const token = await getFirebaseToken(true)
  if (!token) throw new Error('Authentication required')

  return apiFetch(`/api/v1/submissions/${id}/restore`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({}),
  })
}

// ── Admin: Download a private submission file via backend proxy ───────────────

/**
 * Download a private submission file through the backend proxy endpoint.
 *
 * Supports both downloadSubmissionFile(fileId, filename) and legacy downloadSubmissionFile(token, fileId, filename).
 *
 * @param {string} tokenOrFileId  File UUID or legacy token
 * @param {string} fileIdOrFilename Original filename or file UUID
 * @param {string} [maybeFilename] Original filename if token was passed first
 * @returns {Promise<void>}  Triggers browser file save
 */
export async function downloadSubmissionFile(tokenOrFileId, fileIdOrFilename, maybeFilename) {
  let fileId, filename
  if (maybeFilename !== undefined) {
    fileId = fileIdOrFilename
    filename = maybeFilename
  } else {
    fileId = tokenOrFileId
    filename = fileIdOrFilename
  }

  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required')

  const url = getApiUrl(`/api/v1/submissions/files/${fileId}/download`)
  const response = await fetch(url, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const resBody = await response.json()
      detail = resBody?.detail || resBody?.message || detail
    } catch {
      // ignore — response may not be JSON for binary errors
    }
    throw new Error(detail)
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename || 'download'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
}

