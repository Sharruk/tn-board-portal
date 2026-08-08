// =============================================================================
// Submissions Service — frontend/src/services/submissions.js
// =============================================================================
// API calls for the material submission feature.
//
// Public:
//   createSubmission(formData)  — POST /api/v1/submissions  (multipart)
//
// Admin (requires Supabase session token in Authorization header):
//   getSubmissions(token, status)          — GET /api/v1/submissions
//   getSubmission(token, id)               — GET /api/v1/submissions/{id}
//   approveSubmission(token, id, body)     — POST /api/v1/submissions/{id}/approve
//   rejectSubmission(token, id, body)      — POST /api/v1/submissions/{id}/reject
// =============================================================================

import { API_BASE_URL, apiFetch } from '../lib/api'

// ── Public ────────────────────────────────────────────────────────────────────

/**
 * Submit educational material (public — no auth required).
 *
 * @param {FormData} formData  Must include: publisher_name, email, files[].
 *                             Optional: details.
 * @returns {Promise<{ id: string, status: string, message: string }>}
 */
export async function createSubmission(formData) {
  // We use raw fetch here (not apiFetch) because we need multipart/form-data
  // without setting Content-Type manually — the browser sets boundary automatically.
  const url = `${API_BASE_URL}/api/v1/submissions`
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
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

// ── Admin helpers ─────────────────────────────────────────────────────────────

function adminHeaders(token) {
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
}

// ── Admin: List submissions ───────────────────────────────────────────────────

/**
 * List all submissions (admin only).
 *
 * @param {string} token    Supabase session access_token
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
 * @param {string} token  Supabase session access_token
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
 * @param {string} token  Supabase session access_token
 * @param {string} id     Submission UUID
 * @param {{ subject_id: number, exam_type: string, year: number, paper_type: string, month?: string, district?: string }} body
 * @returns {Promise<{ submission_id: string, status: string, paper_ids: number[] }>}
 */
export async function approveSubmission(token, id, body) {
  const url = `${API_BASE_URL}/api/v1/submissions/${id}/approve`
  const response = await fetch(url, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const resBody = await response.json()
      detail = resBody?.detail || resBody?.message || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return response.json()
}

// ── Admin: Reject submission ──────────────────────────────────────────────────

/**
 * Reject a pending submission.
 *
 * @param {string} token  Supabase session access_token
 * @param {string} id     Submission UUID
 * @param {{ rejection_reason?: string }} body
 * @returns {Promise<{ submission_id: string, status: string, rejection_reason: string|null }>}
 */
export async function rejectSubmission(token, id, body) {
  const url = `${API_BASE_URL}/api/v1/submissions/${id}/reject`
  const response = await fetch(url, {
    method: 'POST',
    headers: adminHeaders(token),
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const resBody = await response.json()
      detail = resBody?.detail || resBody?.message || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return response.json()
}
