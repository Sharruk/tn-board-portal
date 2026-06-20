import { supabase } from '../lib/supabase'

export const EXAM_TYPES = [
  'Unit Test 1', 'Unit Test 2', 'Unit Test 3',
  'Quarterly Exam', 'Half Yearly Exam',
  'Annual Exam', 'Public Exam', 'Practical Exam', 'Model Exam',
]

export const getPaper = async (id) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*, subjects ( *, classes ( * ) )')
    .eq('id', id)
    .eq('is_visible', true)
    .single()
  if (error) throw error
  return { data }
}

export const getPaperBySlug = async (slug) => {
  const parts = slug.split('-')
  const id = parseInt(parts[parts.length - 1], 10)
  if (isNaN(id)) throw new Error('Paper not found')
  return getPaper(id)
}

export const getRecentPapers = async (limit = 10) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .eq('is_visible', true)
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw error
  return { data }
}

export const getPopularPapers = async (limit = 10) => {
  const { data, error } = await supabase
    .from('papers')
    .select('*')
    .eq('is_visible', true)
    .order('download_count', { ascending: false })
    .limit(limit)
  if (error) throw error
  return { data }
}

export const getExamTypes = () =>
  Promise.resolve({ data: { exam_types: EXAM_TYPES } })

export const recordDownload = async (id) => {
  const { error } = await supabase.rpc('increment_download_count', {
    paper_id_param: id,
  })
  if (error) throw error
}
