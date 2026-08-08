// =============================================================================
// Subjects Service — migrated to FastAPI
// =============================================================================
// All requests now go through FastAPI DEV:
//   GET /api/v1/subjects/{subject_id}        ← getSubject
//   GET /api/v1/papers/by-subject/{id}       ← getPapersForSubject
//
// Public function signatures and return shapes are preserved so that
// components (SubjectPage, PaperListPage, PaperDetailPage) require zero changes.
// =============================================================================

import { apiFetch } from '../lib/api'

/**
 * Fetch a single subject by id, including parent class information.
 *
 * FastAPI returns a flat SubjectResponse:
 *   { id, class_id, name, slug, is_practical, display_order,
 *     class_name, class_slug, paper_count }
 *
 * We preserve the shape that components expect:
 *   { data: { ...subject, class_name, class_slug } }
 *
 * @param {number|string} id
 * @returns {Promise<{ data: SubjectResponse }>}
 */
export const getSubject = async (id) => {
  const data = await apiFetch(`/api/v1/subjects/${id}`)
  // FastAPI already includes class_name and class_slug at the top level —
  // no reshaping needed.
  return { data }
}

/**
 * Fetch all papers for a subject, with optional filters.
 *
 * FastAPI returns { data: PaperSummary[], count, limit }.
 * We return { data: [...] } to match the existing shape components expect.
 *
 * @param {number|string} id
 * @param {{ exam_type?: string, paper_type?: string }} [params]
 * @returns {Promise<{ data: PaperSummary[] }>}
 */
export const getPapersForSubject = async (id, params = {}) => {
  const qs = new URLSearchParams()
  if (params.exam_type)  qs.set('exam_type',  params.exam_type)
  if (params.paper_type) qs.set('paper_type', params.paper_type)

  const query = qs.toString() ? `?${qs.toString()}` : ''
  const res = await apiFetch(`/api/v1/papers/by-subject/${id}${query}`)
  // API returns { data: [...], count, limit }
  return { data: res.data }
}
