// =============================================================================
// Classes Service — migrated to FastAPI
// =============================================================================
// All requests now go through FastAPI DEV:
//   GET /api/v1/classes
//   GET /api/v1/classes/{class_id}
//   GET /api/v1/subjects?class_id={id}      ← getSubjectsForClass
//
// Public function signatures and return shapes are preserved so that
// components (HomePage, ClassPage) require zero changes.
// =============================================================================

import { apiFetch } from '../lib/api'

/**
 * Fetch all classes with subject counts.
 * @returns {Promise<{ data: ClassResponse[] }>}
 */
export const getClasses = async () => {
  const res = await apiFetch('/api/v1/classes')
  // API returns { data: [...], count: N }
  return { data: res.data }
}

/**
 * Fetch a single class by id.
 * @param {number|string} id
 * @returns {Promise<{ data: ClassResponse }>}
 */
export const getClass = async (id) => {
  const data = await apiFetch(`/api/v1/classes/${id}`)
  // API returns a flat ClassResponse object (not wrapped)
  return { data }
}

/**
 * Fetch all subjects for a given class.
 * Used by ClassPage — returns subjects with paper_count.
 * @param {number|string} id  class id (9, 10, 11, 12)
 * @returns {Promise<{ data: SubjectResponse[] }>}
 */
export const getSubjectsForClass = async (id) => {
  const res = await apiFetch(`/api/v1/subjects?class_id=${id}`)
  // API returns { data: [...], count: N, class_id: N }
  return { data: res.data }
}
