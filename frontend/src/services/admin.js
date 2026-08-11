import { supabase } from '../lib/supabase'
import { getFirebaseToken, auth } from '../lib/firebase'

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

async function insertAuditLog(action, targetPaperId, targetDetails) {
  const user = await getAuthUser()
  if (!user) return
  await supabase.from('audit_logs').insert({
    admin_id:       user.id,
    admin_email:    user.email,
    action,
    target_paper_id: targetPaperId || null,
    target_details:  targetDetails || null,
  })
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


  const { data, error: insertError } = await supabase
    .from('papers')
    .insert(metadata)
    .select()
    .single()
  if (insertError) throw insertError

  if (onProgress) onProgress(90)

  const action = formData.get('is_bulk') === 'true' ? 'bulk_upload' : 'upload'
  await insertAuditLog(action, data.id, { title: data.title, exam_type: data.exam_type, year: data.year })

  if (onProgress) onProgress(100)

  return { data }
}

export const updatePaper = async (id, updates) => {
  const { data, error } = await supabase
    .from('papers')
    .update(updates)
    .eq('id', id)
    .select()
    .single()
  if (error) throw error
  await insertAuditLog('edit', id, { changes: updates })
  return { data }
}

export const deletePaper = async (id) => {
  const { data: paper, error: fetchError } = await supabase
    .from('papers')
    .select('file_path, title')
    .eq('id', id)
    .single()
  if (fetchError) throw fetchError

  if (paper?.file_path) {
    const { error: storageError } = await supabase.storage.from('papers').remove([paper.file_path])
    if (storageError) throw storageError
  }

  const { error } = await supabase.from('papers').delete().eq('id', id)
  if (error) throw error

  await insertAuditLog('delete', id, { title: paper?.title })
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
  let query = supabase
    .from('audit_logs')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (action) query = query.eq('action', action)
  const { data, error } = await query
  if (error) throw error
  return { data }
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

  const { data, error: insertError } = await supabase
    .from('official_notices')
    .insert(metadata)
    .select()
    .single()
  if (insertError) throw insertError

  if (onProgress) onProgress(90)

  await insertAuditLog('upload_notice', null, { title: data.title, category: data.category, year: data.year })

  if (onProgress) onProgress(100)

  return { data }
}

export const updateNotice = async (id, updates) => {
  const { data, error } = await supabase
    .from('official_notices')
    .update(updates)
    .eq('id', id)
    .select()
    .single()
  if (error) throw error
  await insertAuditLog('edit_notice', null, { id, changes: updates })
  return { data }
}

export const deleteNotice = async (id) => {
  const { data: notice, error: fetchError } = await supabase
    .from('official_notices')
    .select('file_path, title')
    .eq('id', id)
    .single()
  if (fetchError) throw fetchError

  if (notice?.file_path) {
    const { error: storageError } = await supabase.storage
      .from('official-updates')
      .remove([notice.file_path])
    if (storageError) throw storageError
  }

  const { error } = await supabase.from('official_notices').delete().eq('id', id)
  if (error) throw error

  await insertAuditLog('delete_notice', null, { id, title: notice?.title })
}
