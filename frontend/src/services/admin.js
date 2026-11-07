import { supabase } from '../lib/supabase'
import { getFirebaseToken, auth } from '../lib/firebase'
import { apiFetch, getApiUrl } from '../lib/api'

async function getAuthUser() {
  const user = auth.currentUser
  if (user) {
    return {
      id: user.uid,
      email: user.email
    }
  }
  return null
}

// adminLogin is now handled directly via Google Sign-In in LoginPage.jsx
export const adminLogin = async () => {
  throw new Error('Use Google Sign-In via LoginPage')
}

export const getAdminPapers = async () => {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .order('created_at', { ascending: false })
  if (error) throw error
  return { data }
}

export const uploadPaper = async (formData, onProgress) => {
  if (onProgress) onProgress(20)

  const token = await getFirebaseToken()
  const url = getApiUrl('/api/v1/papers')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: formData,
  })

  if (onProgress) onProgress(80)

  if (!response.ok) {
    let detail = `Upload failed (HTTP ${response.status})`
    try {
      const errBody = await response.json()
      detail = errBody?.detail || errBody?.message || detail
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail)
  }

  const data = await response.json()
  if (onProgress) onProgress(100)

  return { data }
}

export const updatePaper = async (id, updates) => {
  const token = await getFirebaseToken()
  const data = await apiFetch(`/api/v1/papers/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(updates),
  })
  return { data }
}

export const deletePaper = async (id) => {
  const token = await getFirebaseToken()
  if (!token) throw new Error('Authentication required to delete papers')

  return await apiFetch(`/api/v1/papers/${id}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
}

export const getAdminStats = async () => {
  const { data, error } = await supabase.rpc('get_admin_stats')
  if (error) throw error
  return { data: data?.[0] ?? null }
}

export const getSearchAnalytics = async () => {
  const { data, error } = await supabase.rpc('get_search_analytics')
  if (error) throw error
  return { data }
}

export const getRecentUploads = async (limit = 20) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*, subjects ( name, classes ( name ) )')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return {
    data: data.map(p => ({
      ...p,
      subject_name: p.subjects?.name,
      class_name:   p.subjects?.classes?.name,
    })),
  }
}

export const getContentStatus = async () => {
  const { data, error } = await supabase.rpc('get_content_status')
  if (error) throw error
  return { data }
}

export const getAdminMe = async () => {
  const user = auth.currentUser
  if (!user) throw new Error('Not authenticated')
  return {
    data: {
      id:       user.uid,
      email:    user.email,
      username: user.email,
    },
  }
}

export const getAuditLogs = async (limit = 50, action = null) => {
  const token = await getFirebaseToken()
  const params = new URLSearchParams()
  if (limit) params.append('limit', String(Math.min(limit, 100)))
  if (action) params.append('action', action)
  const qs = params.toString() ? `?${params.toString()}` : ''
  const res = await apiFetch(`/api/v1/admin/activity-logs${qs}`, {
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  })
  return { data: res?.data || [] }
}

// =============================================================================
// Official Notices Admin CRUD
// Uses the separate "official-updates" Supabase Storage bucket.
// =============================================================================

export const getAdminNotices = async () => {
  const token = await getFirebaseToken()
  try {
    const res = await apiFetch('/api/v1/notices?limit=200', {
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      }
    })
    return { data: res?.data || [] }
  } catch (apiErr) {
    // Fallback to Supabase client if backend is temporarily unreachable
    const { data, error } = await supabase
      .from('official_notices')
      .select('*, classes(name)')
      .order('is_pinned', { ascending: false })
      .order('created_at', { ascending: false })
    if (error) throw error
    return {
      data: data.map(n => ({ ...n, class_name: n.classes?.name ?? null })),
    }
  }
}

/**
 * Upload a notice file and metadata via the backend API with server-side Supabase Storage upload.
 * formData fields:
 *   title, category, class_id (optional), year, description (optional),
 *   expires_at (optional ISO string), youtube_url (optional), file (optional File object)
 */
export const uploadNotice = async (formData, onProgress) => {
  if (onProgress) onProgress(20)

  const token = await getFirebaseToken()
  const url = getApiUrl('/api/v1/notices')

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: formData,
  })

  if (onProgress) onProgress(80)

  if (!response.ok) {
    let detail = `Upload failed (HTTP ${response.status})`
    try {
      const errBody = await response.json()
      detail = errBody?.detail || errBody?.message || detail
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail)
  }

  const data = await response.json()
  if (onProgress) onProgress(100)

  return { data }
}

export const updateNotice = async (id, updates) => {
  const token = await getFirebaseToken()
  const data = await apiFetch(`/api/v1/notices/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(updates),
  })
  return { data }
}

export const deleteNotice = async (id) => {
  const token = await getFirebaseToken()
  return await apiFetch(`/api/v1/notices/${id}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
  })
}
