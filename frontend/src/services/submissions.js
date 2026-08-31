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
 * @param {string} token    Firebase access_token
 * @param {string|null} [statusFilter]  'pending' | 'approved' | 'rejected' | null
 * @param {number} [limit]  Max results (default 50)
 * @returns {Promise<{ data: SubmissionListItem[], count: number, status_filter: string|null }>}
 */
export async function getSubmissions(token, statusFilter = null, limit = 50) {
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
 * @param {string} token  Firebase access_token
 * @param {string} id     Submission UUID
 * @returns {Promise<SubmissionOut>}
 */
export async function getSubmission(token, id) {
  return apiFetch(`/api/v1/submissions/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
}

// ── Admin: Approve submission ─────────────────────────────────────────────────

/**
 * Approve a pending submission and create paper record(s).
 *
 * @param {string} token  Firebase access_token
 * @param {string} id     Submission UUID
 * @param {{ title?: string, download_filename?: string, description?: string, youtube_url?: string, subject_id: number, exam_type: string, year: number, paper_type: string, month?: string, district?: string }} body
 * @returns {Promise<{ submission_id: string, status: string, paper_ids: number[] }>}
 */
export async function approveSubmission(token, id, body) {
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
 *
 * @param {string} token  Firebase access_token
 * @param {string} id     Submission UUID
 * @param {{ rejection_reason?: string }} body
 * @returns {Promise<{ submission_id: string, status: string, rejection_reason: string|null }>}
 */
export async function rejectSubmission(token, id, body) {
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
 *
 * @param {string} token  Firebase access_token
 * @param {string} id     Submission UUID
 * @returns {Promise<{ submission_id: string, status: string }>}
 */
export async function restoreSubmission(token, id) {
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
 * The HTML `download` attribute is silently ignored by browsers for
 * cross-origin URLs (the Supabase signed URL is cross-origin). This
 * function calls our backend proxy which returns the file with
 * Content-Disposition: attachment, so the browser saves it locally.
 *
 * @param {string} token    Firebase access_token
 * @param {string} fileId   UUID from submission_files table
 * @param {string} filename Original filename for the saved file
 * @returns {Promise<void>}  Triggers browser file save
 */
export async function downloadSubmissionFile(token, fileId, filename) {
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

