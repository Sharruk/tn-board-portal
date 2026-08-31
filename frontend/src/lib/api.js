// =============================================================================
// FastAPI Client — lib/api.js
// =============================================================================
// Centralised HTTP client for the FastAPI backend.
// In Vercel unified deployment, backend and frontend share the same origin,
// so API_BASE_URL defaults to an empty string '' (relative path /api/v1/...).
//
// For local development, requests are proxied via Vite (or VITE_API_BASE_URL).
//
// Usage:
//   import { apiFetch } from '../lib/api'
//   const data = await apiFetch('/api/v1/classes')
// =============================================================================

function resolveApiBaseUrl() {
  const envUrl = import.meta.env.VITE_API_BASE_URL || ''
  // If envUrl contains decommissioned render or running on Vercel production domain, use same-origin relative path
  if (envUrl.includes('onrender.com') || envUrl.includes('render.com')) {
    return ''
  }
  if (typeof window !== 'undefined' && (window.location.hostname.endsWith('vercel.app') || window.location.hostname === 'tn-board-portal.vercel.app')) {
    return ''
  }
  return envUrl
}

const API_BASE_URL = resolveApiBaseUrl()

/**
 * Thin fetch wrapper for the FastAPI backend.
 *
 * @param {string} path   - Path relative to API_BASE_URL, e.g. '/api/v1/classes'
 * @param {RequestInit} [options] - Fetch options (method, body, headers, …)
 * @returns {Promise<any>} Parsed JSON response body
 * @throws {Error} on non-2xx HTTP status or network failure
 */
export async function apiFetch(path, options = {}) {
  const baseUrl = resolveApiBaseUrl()
  const url = `${baseUrl}${path}`
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

export function getApiUrl(path) {
  const baseUrl = resolveApiBaseUrl()
  return `${baseUrl}${path}`
}

export { API_BASE_URL }



