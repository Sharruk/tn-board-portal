import { supabase } from '../lib/supabase'

async function getAuthUser() {
  const { data: { user } } = await supabase.auth.getUser()
  return user
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

export const adminLogin = async (email, password) => {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  await insertAuditLog('login_success', null, { identifier: email })
  return { data }
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
    subject_id:    parseInt(formData.get('subject_id'), 10),
    exam_type:     formData.get('exam_type'),
    year:          parseInt(formData.get('year'), 10),
    title:         formData.get('title'),
    paper_type:    formData.get('paper_type'),
    youtube_url:   formData.get('youtube_url') || null,
    file_path:     filename,
    public_url:    publicUrl,
    status:        'draft',
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
  const { data: { user }, error } = await supabase.auth.getUser()
  if (error) throw error
  return {
    data: {
      id:       user.id,
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
