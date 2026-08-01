import { supabase } from '../lib/supabase'

// =============================================================================
// Paper metadata constants — single source of truth for the entire app.
// Import these in admin pages and search — do NOT duplicate locally.
// =============================================================================

export const EXAM_TYPES = [
  'Monthly Test',
  'First Mid Term Test',
  'Unit Test 1',
  'Unit Test 2',
  'Unit Test 3',
  'Quarterly Exam',
  'Half Yearly Exam',
  'Annual Exam',
  'Public Exam',
  'Practical Exam',
  'Model Exam',
]

export const MONTHS = [
  'January', 'February', 'March', 'April',
  'May', 'June', 'July', 'August',
  'September', 'October', 'November', 'December',
]

// All 38 Tamil Nadu districts — alphabetically sorted.
export const TN_DISTRICTS = [
  'Ariyalur',
  'Chengalpattu',
  'Chennai',
  'Coimbatore',
  'Cuddalore',
  'Dharmapuri',
  'Dindigul',
  'Erode',
  'Kallakurichi',
  'Kancheepuram',
  'Kanyakumari',
  'Karur',
  'Krishnagiri',
  'Madurai',
  'Mayiladuthurai',
  'Nagapattinam',
  'Namakkal',
  'Nilgiris',
  'Perambalur',
  'Pudukkottai',
  'Ramanathapuram',
  'Ranipet',
  'Salem',
  'Sivaganga',
  'Tenkasi',
  'Thanjavur',
  'Theni',
  'Thoothukudi',
  'Tiruchirappalli',
  'Tirunelveli',
  'Tirupathur',
  'Tiruppur',
  'Tiruvallur',
  'Tiruvannamalai',
  'Tiruvarur',
  'Vellore',
  'Villupuram',
  'Virudhunagar',
]

// =============================================================================
// Paper service functions
// =============================================================================

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
