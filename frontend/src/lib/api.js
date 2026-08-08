// =============================================================================
// FastAPI Client — lib/api.js
// =============================================================================
// Centralised HTTP client for the FastAPI DEV backend.
// Base URL is read from VITE_API_BASE_URL (set in .env.local for local dev
// and in Vercel/Render environment variables for deployed environments).
//
// Usage:
//   import { apiFetch } from '../lib/api'
//   const data = await apiFetch('/api/v1/classes')
// =============================================================================

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'https://tn-board-portal-api-dev.onrender.com'

if (!import.meta.env.VITE_API_BASE_URL) {
  console.warn(
    '⚠️  VITE_API_BASE_URL is not set.\n' +
    'Add it to frontend/.env.local for local dev:\n' +
    '  VITE_API_BASE_URL=https://tn-board-portal-api-dev.onrender.com\n' +
    'Falling back to the DEV backend URL.'
  )
}

/**
 * Thin fetch wrapper for the FastAPI backend.
 *
 * @param {string} path   - Path relative to API_BASE_URL, e.g. '/api/v1/classes'
 * @param {RequestInit} [options] - Fetch options (method, body, headers, …)
 * @returns {Promise<any>} Parsed JSON response body
 * @throws {Error} on non-2xx HTTP status or network failure
 */
export async function apiFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path}`
  const response = await fetch(url, {
    headers: {
      'Accept': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  // 204 No Content (e.g. POST /papers/{id}/download) — return null
  if (response.status === 204) return null

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

export { API_BASE_URL }
