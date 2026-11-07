import { supabase } from '../lib/supabase'
import { getFirebaseToken, auth } from '../lib/firebase'
import { apiFetch } from '../lib/api'

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
  const file      = formData.get('file')
  const ext       = file.name.split('.').pop().toLowerCase()
  const filename  = `${crypto.randomUUID()}.${ext}`

  if (onProgress) onProgress(10)

  const { error: uploadError } = await supabase.storage
    .from('papers')
    .upload(filename, file, { contentType: 'application/pdf', upsert: false })
  if (uploadError) throw uploadError

  if (onProgress) onProgress(60)

  const { data: { publicUrl } } = supabase.storage
    .from('papers')
    .getPublicUrl(filename)

  const metadata = {
    subject_id:        parseInt(formData.get('subject_id'), 10),
    exam_type:         formData.get('exam_type'),
    year:              parseInt(formData.get('year'), 10),
    month:             formData.get('month') || null,
    district:          formData.get('district') || null,
    title:             formData.get('title'),
    paper_type:        formData.get('paper_type'),
    youtube_url:       formData.get('youtube_url') || null,
    file_path:         filename,
    public_url:        publicUrl,
    original_filename: file.name || null,
    is_visible:        false,
  }

  const token = await getFirebaseToken()
  const data = await apiFetch('/api/v1/papers', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(metadata),
  })

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

/**
 * Upload a notice file to the "official-updates" bucket and insert a DB row.
 * formData fields expected:
 *   title, category, class_id (optional), year, description (optional),
 *   expires_at (optional ISO string), file (File object)
 */
export const uploadNotice = async (formData, onProgress) => {
  const file     = formData.get('file')
  const ext      = file.name.split('.').pop().toLowerCase()
  const filename = `${crypto.randomUUID()}.${ext}`

  // Determine file type for preview strategy
  const FILE_TYPE_MAP = {
    pdf: 'pdf',
    jpg: 'image', jpeg: 'image', png: 'image', gif: 'image', webp: 'image', svg: 'image',
    doc: 'docx', docx: 'docx',
    xls: 'xlsx', xlsx: 'xlsx',
    ppt: 'pptx', pptx: 'pptx',
  }
  const fileType = FILE_TYPE_MAP[ext] ?? 'other'

  if (onProgress) onProgress(10)

  const { error: uploadError } = await supabase.storage
    .from('official-updates')
    .upload(filename, file, { upsert: false })
  if (uploadError) throw uploadError

  if (onProgress) onProgress(60)

  const { data: { publicUrl } } = supabase.storage
    .from('official-updates')
    .getPublicUrl(filename)

  const classIdRaw = formData.get('class_id')
  const expiresAtRaw = formData.get('expires_at')

  const metadata = {
    title:       formData.get('title'),
    category:    formData.get('category'),
    class_id:    classIdRaw ? parseInt(classIdRaw, 10) : null,
    year:        parseInt(formData.get('year'), 10),
    description: formData.get('description') || null,
    youtube_url: formData.get('youtube_url') || null,
    file_path:   filename,
    public_url:  publicUrl,
    file_type:   fileType,
    expires_at:  expiresAtRaw || null,
    is_visible:  false,
    is_pinned:   false,
  }

  const token = await getFirebaseToken()
  const data = await apiFetch('/api/v1/notices', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(metadata),
  })

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
