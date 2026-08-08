// =============================================================================
// Papers Service — migrated to FastAPI
// =============================================================================
// All data-fetching requests now go through FastAPI DEV:
//   GET /api/v1/papers?sort=recent&limit=N   ← getRecentPapers
//   GET /api/v1/papers?sort=popular&limit=N  ← getPopularPapers
//   GET /api/v1/papers/{paper_id}            ← getPaper
//   POST /api/v1/papers/{paper_id}/download  ← recordDownload
//
// Public function signatures and return shapes are preserved so that
// all components (HomePage, PaperDetailPage) require zero changes.
//
// NOTE: Constants (EXAM_TYPES, MONTHS, TN_DISTRICTS) are pure data —
// no Supabase involved — they remain unchanged.
// =============================================================================

import { apiFetch } from '../lib/api'

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
// Adapter — FastAPI flat PaperResponse → Supabase-compatible nested shape
// =============================================================================
// FastAPI GET /api/v1/papers/{id} returns a flat object:
//   { id, subject_id, subject_name, subject_slug, class_id, class_name, ... }
//
// PaperDetailPage expects the old Supabase nested shape:
//   paper.subjects.name
//   paper.subjects.classes.name
//   paper.subjects.class_id
//
// This adapter reconstructs the nested shape from the flat fields so that
// PaperDetailPage requires zero changes.
// =============================================================================

function adaptPaperDetail(p) {
  return {
    ...p,
    subjects: {
      id:           p.subject_id,
      name:         p.subject_name   ?? null,
      slug:         p.subject_slug   ?? null,
      is_practical: p.is_practical   ?? null,
      class_id:     p.class_id       ?? null,
      classes: {
        id:   p.class_id   ?? null,
        name: p.class_name ?? null,
        slug: p.class_slug ?? null,
      },
    },
  }
}

// =============================================================================
// Paper service functions
// =============================================================================

/**
 * Fetch a single published paper by id with full subject/class detail.
 * Return shape includes nested `subjects` for backward compatibility.
 *
 * @param {number|string} id
 * @returns {Promise<{ data: PaperDetail }>}
 */
export const getPaper = async (id) => {
  const data = await apiFetch(`/api/v1/papers/${id}`)
  return { data: adaptPaperDetail(data) }
}

/**
 * Fetch a paper by slug (e.g. "class-10-maths-annual-2024-42").
 * Extracts the numeric id from the slug suffix and delegates to getPaper().
 *
 * @param {string} slug
 * @returns {Promise<{ data: PaperDetail }>}
 */
export const getPaperBySlug = async (slug) => {
  const parts = slug.split('-')
  const id = parseInt(parts[parts.length - 1], 10)
  if (isNaN(id)) throw new Error('Paper not found')
  return getPaper(id)
}

/**
 * Fetch the N most recently uploaded published papers.
 *
 * @param {number} [limit=10]
 * @returns {Promise<{ data: PaperSummary[] }>}
 */
export const getRecentPapers = async (limit = 10) => {
  const res = await apiFetch(`/api/v1/papers?sort=recent&limit=${limit}`)
  // API returns { data: [...], count, limit }
  return { data: res.data }
}

/**
 * Fetch the N most downloaded published papers.
 *
 * @param {number} [limit=10]
 * @returns {Promise<{ data: PaperSummary[] }>}
 */
export const getPopularPapers = async (limit = 10) => {
  const res = await apiFetch(`/api/v1/papers?sort=popular&limit=${limit}`)
  // API returns { data: [...], count, limit }
  return { data: res.data }
}

/**
 * Returns the list of exam types.
 * Pure data — no API call needed.
 */
export const getExamTypes = () =>
  Promise.resolve({ data: { exam_types: EXAM_TYPES } })

/**
 * Record a paper download by calling the FastAPI download endpoint.
 * POST /api/v1/papers/{id}/download returns 204 No Content on success.
 *
 * @param {number|string} id
 * @returns {Promise<void>}
 */
export const recordDownload = async (id) => {
  await apiFetch(`/api/v1/papers/${id}/download`, { method: 'POST' })
}
