import { supabase } from '../lib/supabase'

export const getSubject = async (id) => {
  const { data, error } = await supabase
    .from('subjects')
    .select('*, classes ( id, name, slug )')
    .eq('id', id)
    .single()
  if (error) throw error
  return {
    data: {
      ...data,
      class_name: data.classes?.name,
      class_slug: data.classes?.slug,
    },
  }
}

export const getPapersForSubject = async (id, params = {}) => {
  let query = supabase
    .from('papers')
    .select('*')
    .eq('subject_id', id)
    .eq('is_visible', true)
    .order('year', { ascending: false })

  if (params.exam_type)  query = query.eq('exam_type', params.exam_type)
  if (params.paper_type) query = query.eq('paper_type', params.paper_type)

  const { data, error } = await query
  if (error) throw error
  return { data }
}
