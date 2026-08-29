/**
 * Analytics Telemetry Service — privacy-conscious event logging & admin dashboard queries.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

function getOrCreateSessionId() {
  try {
    let sid = sessionStorage.getItem('tn_session_id')
    if (!sid) {
      sid = 'sess_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36)
      sessionStorage.setItem('tn_session_id', sid)
    }
    return sid
  } catch {
    return 'sess_anon'
  }
}

/**
 * Log an analytics event (non-blocking).
 */
export async function logAnalyticsEvent(eventType, { paperId, classId, subjectId, metadata } = {}) {
  try {
    const payload = {
      event_type: eventType,
      session_id: getOrCreateSessionId(),
      paper_id: paperId || null,
      class_id: classId || null,
      subject_id: subjectId || null,
      metadata: metadata || {},
    }

    const url = `${API_BASE}/analytics/event`

    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' })
      navigator.sendBeacon(url, blob)
    } else {
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(() => {})
    }
  } catch (err) {
    // Non-blocking telemetry — ignore errors silently
  }
}

export function trackPageView(path) {
  logAnalyticsEvent('page_view', { metadata: { path: path || window.location.pathname } })
}

export function trackPaperView(paperId, classId, subjectId) {
  logAnalyticsEvent('paper_view', { paperId, classId, subjectId })
}

export function trackDownload(paperId) {
  logAnalyticsEvent('download', { paperId })
}

export function trackSearch(query, resultCount) {
  if (!query || !query.trim()) return
  logAnalyticsEvent('search', { metadata: { q: query.trim(), count: resultCount } })
}

/**
 * Fetch Analytics Dashboard for Admin.
 */
export async function getAnalyticsDashboard(token) {
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/analytics/dashboard`, { headers })
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || 'Failed to load analytics dashboard')
  }
  return res.json()
}
