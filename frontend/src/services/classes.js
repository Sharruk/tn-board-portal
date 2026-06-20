import { supabase } from '../lib/supabase'

export const getClasses = async () => {
  const { data, error } = await supabase
    .from('classes')
    .select('*, subjects(count)')
    .order('id')
  if (error) throw error
  return {
    data: data.map(c => ({
      ...c,
      subject_count: c.subjects?.[0]?.count ?? 0,
    })),
  }
}

export const getClass = async (id) => {
  const { data, error } = await supabase
    .from('classes')
    .select('*, subjects(count)')
    .eq('id', id)
    .single()
  if (error) throw error
  return {
    data: { ...data, subject_count: data.subjects?.[0]?.count ?? 0 },
  }
}

export const getSubjectsForClass = async (id) => {
  const { data, error } = await supabase
    .from('subjects')
    .select(`
      id, name, slug, is_practical, display_order, class_id,
      classes ( name ),
      papers ( count )
    `)
    .eq('class_id', id)
    .order('display_order')
  if (error) throw error
  return {
    data: data.map(s => ({
      ...s,
      class_name: s.classes?.name,
      paper_count: s.papers?.[0]?.count ?? 0,
    })),
  }
}
